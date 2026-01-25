# ============================================================
# TS4 Mod Analyzer — Phase 1 → Phase 3 (Hugging Face IA)
# Version: v3.5.4
#
# Contract:
# - Phase 1 preserved (identity extraction)
# - Phase 2 preserved (deterministic Notion match)
# - Phase 3 preserved (IA last resort, MAY confirm FOUND)
# - ADDITIVE ONLY:
#   • Deterministic cache (stores FINAL decision)
#   • Canonical decision log (1 entry per mod, explains WHY)
#
# Rule: New version = SUM, never subtraction
# ============================================================

import streamlit as st
import requests
import re
import json
import hashlib
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from notion_client import Client
from datetime import datetime

# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="TS4 Mod Analyzer — Phase 3 · v3.5.4",
    layout="centered"
)

# =========================
# SESSION STATE
# =========================

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "ai_logs" not in st.session_state:
    st.session_state.ai_logs = []

if "decision_log" not in st.session_state:
    st.session_state.decision_log = []

if "cache" not in st.session_state:  # legado, preservado
    st.session_state.cache = {}

if "matchcache" not in st.session_state:
    st.session_state.matchcache = {}

if "notfoundcache" not in st.session_state:
    st.session_state.notfoundcache = {}

if "notioncache_loaded" not in st.session_state:
    st.session_state.notioncache_loaded = False

# =========================
# CONFIG
# =========================

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# =========================
# NOTION CLIENT
# =========================

NOTION_TOKEN = st.secrets["notion"]["token"]
NOTION_DATABASE_ID = st.secrets["notion"]["database_id"]
notion = Client(auth=NOTION_TOKEN)

# =========================
# HUGGING FACE (IA)
# =========================

HF_TOKEN = st.secrets["huggingface"]["token"]
HF_HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

HF_PRIMARY_MODEL = "https://api-inference.huggingface.co/models/google/flan-t5-base"
PHASE3_CONFIDENCE_THRESHOLD = 0.93

# =========================
# UTILS
# =========================

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def now():
    return datetime.utcnow().isoformat()

def upsert_decision_log(identity_hash: str, decision: dict):
    for i, entry in enumerate(st.session_state.decision_log):
        if entry.get("identity_hash") == identity_hash:
            st.session_state.decision_log[i] = decision
            return
    st.session_state.decision_log.append(decision)

# =========================
# PATCH — IDENTITY HASH CANÔNICO (C4)
# =========================

def build_identity_hash(identity: dict) -> str:
    canonical_identity = {
        "url": identity["url"],
        "mod_name": identity["mod_name"],
    }
    return sha256(json.dumps(canonical_identity, sort_keys=True))

# =========================
# NOTIONCACHE LOADER
# =========================

def load_notioncache(data: dict):
    st.session_state.matchcache = data.get("matchcache", {})
    st.session_state.notfoundcache = data.get("notfoundcache", {})
    st.session_state.notioncache_loaded = True
    st.session_state.analysis_result = None

# =========================
# SNAPSHOT (BACKUP / RESTORE) — C3
# =========================

def build_snapshot():
    return {
        "meta": {
            "version": "v3.5.4",
            "generated_at": now(),
        },
        "matchcache": st.session_state.matchcache,
        "notfoundcache": st.session_state.notfoundcache,
        "decision_log": st.session_state.decision_log,
    }

def load_snapshot(snapshot: dict):
    st.session_state.matchcache = snapshot.get("matchcache", {})
    st.session_state.notfoundcache = snapshot.get("notfoundcache", {})
    st.session_state.decision_log = snapshot.get("decision_log", [])
    st.session_state.analysis_result = None
    st.session_state.notioncache_loaded = True

# =========================
# FETCH
# =========================

def fetch_page(url: str) -> str:
    try:
        r = requests.get(url, headers=REQUEST_HEADERS, timeout=25)
        return r.text or ""
    except Exception:
        return ""

# =========================
# PHASE 1 — IDENTIDADE (INALTERADA)
# =========================

def extract_identity(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    page_title = soup.title.get_text(strip=True) if soup.title else None
    og_title = None
    og_site = None

    for meta in soup.find_all("meta"):
        if meta.get("property") == "og:title":
            og_title = meta.get("content", "").strip()
        if meta.get("property") == "og:site_name":
            og_site = meta.get("content", "").strip()

    parsed = urlparse(url)
    slug = parsed.path.strip("/").replace("-", " ").replace("/", " ").strip()

    blocked_patterns = r"(just a moment|cloudflare|access denied|checking your browser|patreon)"
    is_blocked = bool(
        re.search(blocked_patterns, html.lower())
        or (page_title and re.search(blocked_patterns, page_title.lower()))
    )

    return {
        "page_title": page_title,
        "og_title": og_title,
        "og_site": og_site,
        "url_slug": slug,
        "domain": parsed.netloc.replace("www.", ""),
        "is_blocked": is_blocked,
    }

def normalize_name(raw: str) -> str:
    if not raw:
        return "—"
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = re.sub(r"(by\s+[\w\s]+)$", "", cleaned, flags=re.I).strip()
    return cleaned.title() if cleaned.islower() else cleaned

def analyze_url(url: str) -> dict:
    html = fetch_page(url)
    raw = extract_identity(html, url)
    raw_name = raw["page_title"] or raw["og_title"] or raw["url_slug"]

    return {
        "url": url,
        "mod_name": normalize_name(raw_name),
        "debug": raw,
    }

# =========================
# PHASE 2 — NOTION MATCH
# =========================

def search_notion_candidates(mod_name: str, url: str) -> list:
    candidates = []

    try:
        r = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={"property": "URL", "url": {"equals": url}},
        )
        candidates.extend(r["results"])
    except Exception:
        pass

    try:
        r = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={"property": "Filename", "title": {"contains": mod_name}},
        )
        candidates.extend(r["results"])
    except Exception:
        pass

    return list({c["id"]: c for c in candidates}.values())

# =========================
# PHASE 3 — IA
# =========================

def slug_quality(slug: str) -> str:
    return "poor" if not slug or len(slug.split()) <= 2 else "good"

def build_ai_payload(identity, candidates):
    return {
        "identity": {
            "title": identity["mod_name"],
            "domain": identity["debug"]["domain"],
            "slug": identity["debug"]["url_slug"],
            "page_blocked": identity["debug"]["is_blocked"],
        },
        "candidates": [
            {
                "notion_id": c["id"],
                "title": c["properties"]["Filename"]["title"][0]["plain_text"],
            }
            for c in candidates
            if c["properties"]["Filename"]["title"]
        ],
    }

def call_primary_model(payload):
    prompt = f"""
Compare the mod identity with the candidates.

Rules:
- Return JSON only
- match=true only if EXACTLY ONE clear match exists
- Include confidence (0–1)
- Do not guess

Payload:
{json.dumps(payload, ensure_ascii=False)}
"""
    r = requests.post(
        HF_PRIMARY_MODEL,
        headers=HF_HEADERS,
        json={"inputs": prompt, "parameters": {"temperature": 0}},
    )

    try:
        data = r.json()
        text = data[0].get("generated_text") if isinstance(data, list) else data.get("generated_text")
        return json.loads(text) if text else None
    except Exception:
        return None

def log_ai_event(stage, payload, result):
    st.session_state.ai_logs.append({
        "timestamp": now(),
        "stage": stage,
        "payload": payload,
        "result": result,
    })

# =========================
# UI — HEADER
# =========================

st.title("TS4 Mod Analyzer — Phase 3")
st.caption("Determinístico · Auditável · Zero achismo")

# =========================
# IMPORTAÇÃO OBRIGATÓRIA
# =========================

st.subheader("📥 Importar notioncache (obrigatório)")

uploaded_cache = st.file_uploader(
    "notioncache_YYYY-MM-DD_HH-MM.json",
    type="json",
    accept_multiple_files=False
)

if uploaded_cache:
    try:
        cache_data = json.load(uploaded_cache)
        load_notioncache(cache_data)
        st.success("Notioncache importado com sucesso.")
    except Exception:
        st.error("Arquivo de notioncache inválido.")

if not st.session_state.notioncache_loaded:
    st.warning("Importe o notioncache antes de analisar qualquer mod.")
    st.stop()

# =========================
# UI — ANALYSIS
# =========================

url_input = st.text_input("URL do mod")

if st.button("Analisar") and url_input.strip():
    identity = analyze_url(url_input.strip())
    identity_hash = build_identity_hash(identity)

    # C2 — cache hit também gera log canônico
    if identity_hash in st.session_state.matchcache:
        decision = st.session_state.matchcache[identity_hash]
        upsert_decision_log(identity_hash, decision)
        st.session_state.analysis_result = decision
        st.stop()

    if identity_hash in st.session_state.notfoundcache:
        decision = st.session_state.notfoundcache[identity_hash]
        upsert_decision_log(identity_hash, decision)
        st.session_state.analysis_result = decision
        st.stop()

    candidates = search_notion_candidates(identity["mod_name"], identity["url"])

    decision = {
        "timestamp": now(),
        "identity_hash": identity_hash,
        "identity": identity,
        "phase_2_candidates": len(candidates),
        "phase_2_status": None,
        "decision": None,
        "reason": None,
    }

    if len(candidates) == 1:
        decision["phase_2_status"] = "UNIQUE"
        decision["decision"] = "FOUND"
        decision["reason"] = "Unique deterministic match in Phase 2"
        st.session_state.matchcache[identity_hash] = decision

    elif len(candidates) > 1:
        decision["phase_2_status"] = "AMBIGUOUS"

        if identity["debug"]["is_blocked"] or slug_quality(identity["debug"]["url_slug"]) == "poor":
            payload = build_ai_payload(identity, candidates)
            ai_result = call_primary_model(payload)
            log_ai_event("PHASE_3_CALLED", payload, ai_result)

            if (
                ai_result
                and ai_result.get("match") is True
                and ai_result.get("confidence", 0) >= PHASE3_CONFIDENCE_THRESHOLD
            ):
                decision["decision"] = "FOUND"
                decision["reason"] = f"Phase 3 confirmed unique match (confidence {ai_result['confidence']})"
                st.session_state.matchcache[identity_hash] = decision
            else:
                decision["decision"] = "NOT_FOUND"
                decision["reason"] = "Ambiguous candidates; IA did not confirm unique match"
                st.session_state.notfoundcache[identity_hash] = decision
        else:
            decision["decision"] = "NOT_FOUND"
            decision["reason"] = "Ambiguous candidates with strong identity; IA skipped"
            st.session_state.notfoundcache[identity_hash] = decision

    else:
        decision["phase_2_status"] = "NONE"
        decision["decision"] = "NOT_FOUND"
        decision["reason"] = "No deterministic candidates in Phase 2"
        st.session_state.notfoundcache[identity_hash] = decision

    upsert_decision_log(identity_hash, decision)
    st.session_state.analysis_result = decision

# =========================
# UI — RESULT
# =========================

result = st.session_state.analysis_result

if result:
    st.subheader("📦 Mod")
    st.write(result["identity"]["mod_name"])
    st.success(result["decision"])

    with st.expander("🔍 Debug técnico"):
        st.json(result)

# =========================
# DOWNLOADS — CACHE / LOG
# =========================

st.divider()
st.subheader("📁 Dados persistentes")

with st.expander("🗃️ Baixar cache"):
    st.download_button(
        "FOUND — matchcache",
        data=json.dumps(st.session_state.matchcache, indent=2, ensure_ascii=False),
        file_name="ts4_mod_matchcache.json",
        mime="application/json",
    )

    st.download_button(
        "NOT_FOUND — notfoundcache",
        data=json.dumps(st.session_state.notfoundcache, indent=2, ensure_ascii=False),
        file_name="ts4_mod_notfoundcache.json",
        mime="application/json",
    )

with st.expander("📊 Baixar logs"):
    st.download_button(
        "Log canônico",
        data=json.dumps(st.session_state.decision_log, indent=2, ensure_ascii=False),
        file_name="ts4_mod_canonical_log.json",
        mime="application/json",
    )

    st.download_button(
        "Log técnico (IA)",
        data=json.dumps(st.session_state.ai_logs, indent=2, ensure_ascii=False),
        file_name="ts4_mod_technical_log.json",
        mime="application/json",
    )

st.download_button(
    "📦 Baixar snapshot completo (JSON)",
    data=json.dumps(build_snapshot(), indent=2, ensure_ascii=False),
    file_name="ts4_mod_snapshot_v3.5.4.json",
    mime="application/json",
)

# =========================
# FOOTER (CANÔNICO — PRESERVADO)
# =========================

st.markdown(
    """
    <div style="text-align:center;padding:1rem 0;font-size:0.85rem;color:#6b7280;">
        <img src="https://64.media.tumblr.com/05d22b63711d2c391482d6faad367ccb/675ea15a79446393-0d/s2048x3072/cc918dd94012fe16170f2526549f3a0b19ecbcf9.png"
             style="height:20px;vertical-align:middle;margin-right:6px;">
        Criado por Akin (@UnpaidSimmer)
        <div style="font-size:0.7rem;opacity:0.6;">v3.5.4 · Phase 3 (IA controlada)</div>
    </div>
    """,
    unsafe_allow_html=True,
)
