# ============================================================
# TS4 Mod Analyzer — Phase 2 Sandbox
# Version: v3.4
# Purpose: Duplicate detection (NO Notion writes)
# ============================================================

import streamlit as st
import requests
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# =========================
# SESSION STATE
# =========================

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "duplication_result" not in st.session_state:
    st.session_state.duplication_result = None

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="TS4 Mod Analyzer — v3.4",
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
# MOCK NOTION DATABASE
# =========================

MOCK_NOTION_DB = [
    {"mod_name": "Mini Fixes", "creator": "Kuttoe"},
    {"mod_name": "Small Bug Fixes", "creator": "LittleMsSam"},
    {"mod_name": "Automatic Beard Shadows", "creator": "Someone"},
]

# =========================
# FETCH
# =========================

def fetch_page(url: str) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    if response.status_code in (403, 429):
        return response.text
    response.raise_for_status()
    return response.text

# =========================
# PHASE 1 — IDENTITY
# =========================

def extract_identity(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    page_title = soup.title.string.strip() if soup.title else None

    og_title = None
    og_site = None
    for meta in soup.find_all("meta"):
        if meta.get("property") == "og:title":
            og_title = meta.get("content", "").strip()
        if meta.get("property") == "og:site_name":
            og_site = meta.get("content", "").strip()

    parsed = urlparse(url)
    slug = parsed.path.strip("/").replace("-", " ").replace("/", " ").strip()

    blocked_patterns = (
        r"(just a moment|403 forbidden|access denied|cloudflare|"
        r"checking your browser|patreon login)"
    )

    is_blocked = bool(
        re.search(blocked_patterns, html.lower())
        or (page_title and re.search(blocked_patterns, page_title.lower()))
    )

    return {
        "page_title": page_title,
        "og_title": og_title,
        "og_site": og_site,
        "url_slug": slug,
        "is_blocked": is_blocked,
        "domain": parsed.netloc.replace("www.", ""),
    }

def normalize_name(raw: str) -> str:
    if not raw:
        return "—"
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = re.sub(r"(by\s+[\w\s]+)$", "", cleaned, flags=re.I).strip()
    return cleaned.title() if cleaned.islower() else cleaned

def normalize_identity(identity: dict) -> dict:
    if not identity["is_blocked"] and identity["page_title"]:
        preferred = identity["page_title"]
    elif identity["og_title"]:
        preferred = identity["og_title"]
    else:
        preferred = identity["url_slug"]

    mod_name = normalize_name(preferred)
    creator = identity["og_site"] or identity["domain"]

    return {
        "mod_name": mod_name,
        "creator": creator or "—",
    }

def analyze_url(url: str) -> dict:
    html = fetch_page(url)
    raw = extract_identity(html, url)
    norm = normalize_identity(raw)

    return {
        "url": url,
        "mod_name": norm["mod_name"],
        "creator": norm["creator"],
        "identity_debug": raw,
    }

# =========================
# PHASE 2 — DUPLICATE SCORE
# =========================

def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    common = a_words & b_words
    return len(common) / max(len(a_words), 1)

def compute_match(candidate, existing):
    score = 0.0
    reasons = []

    name_score = similarity(candidate["mod_name"], existing["mod_name"])
    if name_score > 0:
        score += name_score * 0.4
        reasons.append(f"Nome parecido ({name_score:.2f})")

    if candidate["creator"] == existing["creator"]:
        score += 0.2
        reasons.append("Mesmo criador")

    return round(score, 2), reasons

def detect_duplicate(candidate):
    best = None
    best_score = 0
    best_reasons = []

    for entry in MOCK_NOTION_DB:
        score, reasons = compute_match(candidate, entry)
        if score > best_score:
            best = entry
            best_score = score
            best_reasons = reasons

    return {
        "best_score": best_score,
        "best_match": best,
        "reasons": best_reasons,
    }

# =========================
# UI
# =========================

st.title("TS4 Mod Analyzer — v3.4")
st.markdown(
    "Fase 2 (Sandbox): **detecção de duplicatas**  \n"
    "⚠️ Não escreve no Notion."
)

url_input = st.text_input("URL do mod")

if st.button("Analisar"):
    if not url_input.strip():
        st.warning("Cole uma URL válida.")
    else:
        with st.spinner("Analisando..."):
            result = analyze_url(url_input.strip())
            st.session_state.analysis_result = result
            st.session_state.duplication_result = detect_duplicate(result)

# =========================
# RENDER
# =========================

if st.session_state.analysis_result:
    r = st.session_state.analysis_result
    d = st.session_state.duplication_result

    st.subheader("📦 Identidade")
    st.write("**Mod:**", r["mod_name"])
    st.write("**Criador:**", r["creator"])

    st.subheader("🔎 Verificação de duplicata")

    if d["best_score"] >= 0.5:
        st.error("⚠️ Alta chance de duplicata")
    elif d["best_score"] >= 0.25:
        st.warning("⚠️ Possível duplicata")
    else:
        st.success("✅ Provavelmente novo mod")

    st.write("**Score:**", d["best_score"])

    if d["best_match"]:
        st.write(
            f"**Possível match:** {d['best_match']['mod_name']} — "
            f"{d['best_match']['creator']}"
        )

    if d["reasons"]:
        st.write("**Razões:**")
        for r in d["reasons"]:
            st.write("-", r)

    with st.expander("🔍 Debug Fase 1"):
        st.json(r["identity_debug"])

# =========================
# FOOTER
# =========================


st.markdown(
    """
    <div style="text-align: center; padding: 1rem 0; font-size: 0.9rem; color: #6b7280;">
        <img src="https://64.media.tumblr.com/05d22b63711d2c391482d6faad367ccb/675ea15a79446393-0d/s2048x3072/cc918dd94012fe16170f2526549f3a0b19ecbcf9.png" 
             alt="Favicon" 
             style="height: 20px; vertical-align: middle; margin-right: 8px;">
        Criado por Akin (@UnpaidSimmer) · v3.4 · Sandbox
        <div style="margin-top: 0.5rem; font-size: 0.75rem; opacity: 0.6;">
            v3.3
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
