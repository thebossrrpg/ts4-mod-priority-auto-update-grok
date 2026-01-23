# ============================================================
# TS4 Mod Analyzer — Phase 1 → Phase 3 (Hugging Face IA)
# Version: v3.4.1
#
# Status:
# - Phase 1: Stable (ironclad)
# - Phase 2: Deterministic Notion matching
# - Phase 3: IA (last resort, gated, auditável)
#
# Notes:
# - Nenhuma decisão automática
# - Notion é a base canônica
# - IA apenas compara identidade × candidatos
# ============================================================

import streamlit as st
import requests
import re
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from notion_client import Client
from datetime import datetime

# =========================
# SESSION STATE
# =========================

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="TS4 Mod Analyzer — Phase 2 · v3.4.1",
    layout="centered"
)

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
HF_FALLBACK_MODEL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"

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
# IDENTIDADE (Phase 1)
# =========================

def extract_identity(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    page_title = soup.title.get_text(strip=True) if soup.title else None
    og_title, og_site = None, None

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
        "is_blocked": is_blocked
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
    mod_name = normalize_name(raw_name)

    return {
        "url": url,
        "mod_name": mod_name,
        "debug": raw
    }

# =========================
# PHASE 2 — NOTION MATCH
# =========================

def search_notion_candidates(mod_name: str, url: str) -> list:
    candidates = []

    try:
        r = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={"property": "URL", "url": {"equals": url}}
        )
        candidates.extend(r["results"])
    except Exception:
        pass

    try:
        r = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={"property": "Filename", "title": {"contains": mod_name}}
        )
        candidates.extend(r["results"])
    except Exception:
        pass

    return list({c["id"]: c for c in candidates}.values())

# =========================
# PHASE 3 — HELPERS (PASSO 1)
# =========================

def tokenize(text: str) -> set:
    if not text:
        return set()
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def tokenize_identity(identity: dict) -> set:
    tokens = set()
    tokens |= tokenize(identity["mod_name"])
    tokens |= tokenize(identity["debug"].get("page_title"))
    tokens |= tokenize(identity["debug"].get("og_title"))
    tokens |= tokenize(identity["debug"].get("url_slug"))
    tokens |= tokenize(identity["url"])
    return tokens

def tokenize_candidate(candidate: dict) -> set:
    title = candidate["properties"]["Filename"]["title"]
    text = title[0]["plain_text"] if title else ""
    return tokenize(text)

def strong_token_overlap(identity: dict, candidates: list) -> bool:
    identity_tokens = tokenize_identity(identity)
    for c in candidates:
        overlap = identity_tokens & tokenize_candidate(c)
        if len(overlap) >= 2:
            return True
    return False

def write_phase3_log(identity, primary_result, fallback_result, candidates):
    log = {
        "timestamp": datetime.utcnow().isoformat(),
        "phase": "PHASE_3",
        "identity": identity["mod_name"],
        "page_blocked": identity["debug"]["is_blocked"],
        "primary_model": primary_result,
        "fallback_model": fallback_result,
        "candidates_count": len(candidates),
        "final_state": (
            "MATCH" if primary_result.get("match")
            else "AMBIGUOUS"
        )
    }

    st.download_button(
        label="📄 Baixar log técnico da IA",
        data=json.dumps(log, indent=2, ensure_ascii=False),
        file_name=f"phase3_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

# =========================
# PHASE 3 — IA (EXISTENTE)
# =========================

def slug_quality(slug: str) -> str:
    if not slug or len(slug.split()) <= 2:
        return "poor"
    return "good"

def build_ai_payload(identity, candidates):
    return {
        "identity": {
            "title": identity["mod_name"],
            "domain": identity["debug"]["domain"],
            "slug": identity["debug"]["url_slug"],
            "page_blocked": identity["debug"]["is_blocked"]
        },
        "candidates": [
            {
                "notion_id": c["id"],
                "title": c["properties"]["Filename"]["title"][0]["plain_text"]
            }
            for c in candidates
            if c["properties"]["Filename"]["title"]
        ]
    }

def call_primary_model(payload):
    prompt = f"""
Compare the mod identity with the candidates.

Rules:
- Return JSON only
- match=true only if EXACTLY ONE clear match exists
- Do not guess

Payload:
{json.dumps(payload, ensure_ascii=False)}
"""
    r = requests.post(
        HF_PRIMARY_MODEL,
        headers=HF_HEADERS,
        json={"inputs": prompt, "parameters": {"temperature": 0}}
    )
    return json.loads(r.json()[0]["generated_text"])

# =========================
# UI
# =========================

st.title("TS4 Mod Analyzer — Phase 2")

url_input = st.text_input("URL do mod")

if st.button("Analisar") and url_input.strip():
    with st.spinner("Analisando..."):
        st.session_state.analysis_result = analyze_url(url_input.strip())

result = st.session_state.analysis_result

if result:
    st.subheader("📦 Mod")
    st.write(result["mod_name"])

    with st.expander("🔍 Debug técnico"):
        st.json(result["debug"])

    st.markdown("---")
    st.subheader("Notion")

    candidates = search_notion_candidates(result["mod_name"], result["url"])

    if candidates:
        st.success("Match encontrado no Notion.")
        for c in candidates:
            page_url = f"https://www.notion.so/{c['id'].replace('-', '')}"
            title = c["properties"]["Filename"]["title"][0]["plain_text"]
            st.markdown(f"- [{title}]({page_url})")
    else:
        if result["debug"]["is_blocked"] or slug_quality(result["debug"]["url_slug"]) == "poor":
            st.warning("Identidade fraca — acionando IA (Fase 3)")
            payload = build_ai_payload(result, [])
            primary = call_primary_model(payload)
            if not primary.get("match"):
                write_phase3_log(result, primary, None, [])
            st.info("IA não conseguiu colapsar o match.")
        else:
            st.info("Nenhuma duplicata encontrada.")

# =========================
# FOOTER
# =========================

st.markdown(
    """
    <div style="text-align:center;padding:1rem 0;font-size:0.85rem;color:#6b7280;">
        <img src="https://64.media.tumblr.com/05d22b63711d2c391482d6faad367ccb/675ea15a79446393-0d/s2048x3072/cc918dd94012fe16170f2526549f3a0b19ecbcf9.png"
             style="height:20px;vertical-align:middle;margin-right:6px;">
        Criado por Akin (@UnpaidSimmer)
        <div style="font-size:0.7rem;opacity:0.6;">v3.4.1 · Phase 3 (IA controlada)</div>
    </div>
    """,
    unsafe_allow_html=True
)
