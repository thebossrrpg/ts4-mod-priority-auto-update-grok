# ============================================================
# TS4 Mod Analyzer — Phase 1 → Phase 3 (Hugging Face IA)
# Version: v3.5.0
#
# Contract:
# - Phase 1 preserved (identity extraction)
# - Phase 2 preserved (deterministic Notion match)
# - Phase 3 preserved (IA last resort)
# - ADDITIVE ONLY:
#   • Phase 2 cache (Notion pages = source of truth)
#   • Phase 3 cache (FOUND only)
#   • Canonical decision log (NOT_FOUND)
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
    page_title="TS4 Mod Analyzer — Phase 3 · v3.5.0",
    layout="centered"
)

# =========================
# SESSION STATE
# =========================

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "notion_cache" not in st.session_state:
    st.session_state.notion_cache = {}

if "phase3_cache" not in st.session_state:
    st.session_state.phase3_cache = {}

if "decision_log" not in st.session_state:
    st.session_state.decision_log = []

if "ai_logs" not in st.session_state:
    st.session_state.ai_logs = []

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

# =========================
# UTILS
# =========================

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def now():
    return datetime.utcnow().isoformat()

def fingerprint(obj) -> str:
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False))

# =========================
# PHASE 1 — IDENTIDADE
# =========================

def fetch_page(url: str) -> str:
    try:
        r = requests.get(url, headers=REQUEST_HEADERS, timeout=25)
        return r.text or ""
    except Exception:
        return ""

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

    blocked_patterns = r"(just a moment|cloudflare|access denied|checking your browser)"
    is_blocked = bool(
        re.search(blocked_patterns, html.lower())
        or (page_title and re.search(blocked_patterns, page_title.lower()))
    )

    return {
        "url": url,
        "page_title": page_title,
        "og_title": og_title,
        "og_site": og_site,
        "slug": slug,
        "domain": parsed.netloc.replace("www.", ""),
        "is_blocked": is_blocked,
        "extracted_at": now()
    }

def presentation_name(identity, notion_page=None) -> str:
    if notion_page:
        title = notion_page["properties"]["Filename"]["title"]
        if title:
            return title[0]["plain_text"]

    return (
        identity["og_title"]
        or identity["page_title"]
        or identity["slug"]
        or "—"
    )

# =========================
# PHASE 2 — NOTION CACHE
# =========================

def load_notion_cache():
    pages = {}
    has_more = True
    cursor = None

    while has_more:
        payload = {}
        if cursor:
            payload["start_cursor"] = cursor

        r = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            json=payload
        )

        data = r["results"]
        for page in data:
            pages[page["id"]] = page

        has_more = r.get("has_more", False)
        cursor = r.get("next_cursor")

    return pages

if not st.session_state.notion_cache:
    st.session_state.notion_cache = load_notion_cache()

# =========================
# PHASE 2 — MATCH
# =========================

def search_notion(identity):
    matches = []

    for page in st.session_state.notion_cache.values():
        props = page["properties"]

        url_prop = props.get("URL", {}).get("url")
        title_prop = props.get("Filename", {}).get("title", [])

        if url_prop and url_prop == identity["url"]:
            matches.append(page)
            continue

        if title_prop:
            name = title_prop[0]["plain_text"].lower()
            if identity["slug"].lower() in name:
                matches.append(page)

    return matches

# =========================
# PHASE 3 — IA
# =========================

def build_ai_payload(identity, candidates):
    return {
        "identity": identity,
        "candidates": [
            {
                "id": c["id"],
                "title": c["properties"]["Filename"]["title"][0]["plain_text"]
            }
            for c in candidates
            if c["properties"]["Filename"]["title"]
        ]
    }

def call_primary_model(payload):
    prompt = (
        "Compare the identity with the candidates.\n"
        "Return JSON only.\n"
        "match=true only if exactly ONE clear match exists.\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )

    r = requests.post(
        HF_PRIMARY_MODEL,
        headers=HF_HEADERS,
        json={"inputs": prompt, "parameters": {"temperature": 0}}
    )

    try:
        data = r.json()
        text = data[0].get("generated_text")
        return json.loads(text)
    except Exception:
        return None

# =========================
# UI
# =========================

st.title("TS4 Mod Analyzer — Phase 3")
st.caption("Determinístico · Auditável · Zero achismo")

url_input = st.text_input("URL do mod")

if st.button("Analisar") and url_input.strip():
    html = fetch_page(url_input.strip())
    identity = extract_identity(html, url_input.strip())
    identity_fp = fingerprint(identity)

    # Phase 3 cache hit
    if identity_fp in st.session_state.phase3_cache:
        st.session_state.analysis_result = st.session_state.phase3_cache[identity_fp]
        st.info("⚡ Resultado recuperado do cache (Phase 3)")
    else:
        candidates = search_notion(identity)

        if len(candidates) == 1:
            page = candidates[0]
            record = {
                "decision": "FOUND",
                "identity": identity,
                "notion_page": page,
                "notion_fp": fingerprint(page),
                "resolved_at": now()
            }
            st.session_state.phase3_cache[identity_fp] = record
            st.session_state.analysis_result = record

        else:
            payload = build_ai_payload(identity, candidates)
            ai_result = call_primary_model(payload)

            st.session_state.ai_logs.append({
                "timestamp": now(),
                "payload": payload,
                "result": ai_result
            })

            st.session_state.decision_log.append({
                "timestamp": now(),
                "identity": identity,
                "candidates": [
                    c["properties"]["Filename"]["title"][0]["plain_text"]
                    for c in candidates
                    if c["properties"]["Filename"]["title"]
                ],
                "reason": "Indeterminação na Phase 3",
                "ai_result": ai_result
            })

            st.session_state.analysis_result = {
                "decision": "NOT_FOUND",
                "identity": identity
            }

# =========================
# UI — RESULT
# =========================

result = st.session_state.analysis_result

if result:
    name = presentation_name(
        result["identity"],
        result.get("notion_page")
    )

    st.subheader("📦 Mod")
    st.write(name)

    if result.get("notion_page"):
        page_id = result["notion_page"]["id"].replace("-", "")
        st.markdown(f"[Abrir no Notion](https://www.notion.so/{page_id})")

# =========================
# DOWNLOADS
# =========================

st.divider()

st.download_button(
    "🗃️ Baixar cache Phase 3 (FOUND)",
    json.dumps(st.session_state.phase3_cache, indent=2, ensure_ascii=False),
    "phase3_cache.json",
    "application/json"
)

st.download_button(
    "📊 Baixar log canônico (NOT_FOUND)",
    json.dumps(st.session_state.decision_log, indent=2, ensure_ascii=False),
    "decision_log.json",
    "application/json"
)

# =========================
# FOOTER (CANÔNICO)
# =========================

st.markdown(
    """
    <div style="text-align:center;padding:1rem 0;font-size:0.85rem;color:#6b7280;">
        <img src="https://64.media.tumblr.com/05d22b63711d2c391482d6faad367ccb/675ea15a79446393-0d/s2048x3072/cc918dd94012fe16170f2526549f3a0b19ecbcf9.png"
             style="height:20px;vertical-align:middle;margin-right:6px;">
        Criado por Akin (@UnpaidSimmer)
        <div style="font-size:0.7rem;opacity:0.6;">v3.5.0 · Phase 3 (IA controlada)</div>
    </div>
    """,
    unsafe_allow_html=True
)
