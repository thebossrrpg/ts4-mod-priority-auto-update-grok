# ============================================================
# TS4 Mod Analyzer — Phase 1
# Version: v3.3 (UI/state fix, debug consistente)
# ============================================================

import streamlit as st
import requests
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# =========================
# SESSION STATE INIT
# =========================

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="TS4 Mod Analyzer — Phase 1",
    layout="centered"
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

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
# EXTRAÇÃO DE IDENTIDADE
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

# =========================
# NORMALIZAÇÃO
# =========================

def normalize_name(raw: str) -> str:
    if not raw:
        return "—"
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = re.sub(r"(\b\w+\b)(\s+\1)+$", r"\1", cleaned, flags=re.I)
    cleaned = re.sub(r"(by\s+[\w\s]+)$", "", cleaned, flags=re.I).strip()
    return cleaned.title() if cleaned.islower() else cleaned

def normalize_identity(identity: dict) -> dict:
    preferred_name = None

    if (
        not identity["is_blocked"]
        and identity["page_title"]
        and "just a moment" not in identity["page_title"].lower()
    ):
        preferred_name = identity["page_title"]
    elif identity["og_title"]:
        preferred_name = identity["og_title"]
    else:
        preferred_name = identity["url_slug"]

    mod_name = normalize_name(preferred_name)

    creator = identity["og_site"] or identity["domain"]

    if preferred_name and "by " in preferred_name.lower():
        m = re.search(r"by\s+([\w\s]+)", preferred_name, re.I)
        if m:
            creator = normalize_name(m.group(1))

    return {
        "mod_name": mod_name,
        "creator": creator or "—",
    }

# =========================
# ORQUESTRADOR
# =========================

def analyze_url(url: str) -> dict:
    html = fetch_page(url)
    identity_raw = extract_identity(html, url)
    identity_norm = normalize_identity(identity_raw)

    return {
        "url": url,
        "mod_name": identity_norm["mod_name"],
        "creator": identity_norm["creator"],
        "identity_debug": identity_raw,
    }

# =========================
# UI
# =========================

st.title("TS4 Mod Analyzer — Phase 1")
st.markdown(
    "Cole a **URL de um mod**.  \n"
    "Extrai identidade básica para evitar duplicatas no Notion."
)

url_input = st.text_input(
    "URL do mod",
    placeholder="Cole aqui a URL completa do mod"
)

# -------- AÇÃO --------

if st.button("Analisar"):
    if not url_input.strip():
        st.warning("Cole uma URL válida.")
    else:
        with st.spinner("Analisando..."):
            st.session_state.analysis_result = analyze_url(url_input.strip())

# -------- RENDER PERSISTENTE --------

result = st.session_state.analysis_result

if result:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📦 Mod")
        st.write(result["mod_name"])

    with col2:
        st.subheader("👤 Criador")
        st.write(result["creator"])

    st.success("Identidade extraída com sucesso.")

    with st.expander("🔍 Debug técnico"):
        st.json(result["identity_debug"])

    if result["identity_debug"]["is_blocked"]:
        st.warning(
            "⚠️ Bloqueio detectado (Cloudflare / Patreon). "
            "Fallback aplicado (slug/domínio)."
        )

# =========================
# FOOTER
# =========================

st.markdown(
    """
    <div style="text-align: center; padding: 1rem 0; font-size: 0.9rem; color: #6b7280;">
        <img src="https://64.media.tumblr.com/05d22b63711d2c391482d6faad367ccb/675ea15a79446393-0d/s2048x3072/cc918dd94012fe16170f2526549f3a0b19ecbcf9.png" 
             alt="Favicon" 
             style="height: 20px; vertical-align: middle; margin-right: 8px;">
        Criado por Akin (@UnpaidSimmer)
    </div>
    """,
