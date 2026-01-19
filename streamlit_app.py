# ============================================================
# TS4 Mod Analyzer — Phase 1
# Version: v3.3
# Focus: Patreon / CurseForge block handling (NO LLM)
# ============================================================

import streamlit as st
import requests
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# -------------------------
# PAGE CONFIG
# -------------------------

st.set_page_config(
    page_title="TS4 Mod Analyzer — Phase 1",
    layout="centered"
)

# -------------------------
# CONSTANTS
# -------------------------

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BLOCK_PATTERNS = re.compile(
    r"(just a moment|checking your browser|cloudflare|access denied|"
    r"403 forbidden|patreon is powering|become a patron|enable javascript)",
    re.I
)

# -------------------------
# FETCH
# -------------------------

def fetch_page(url: str) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    return response.text or ""

# -------------------------
# IDENTITY EXTRACTION
# -------------------------

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

    is_blocked = bool(
        BLOCK_PATTERNS.search(html.lower()) or
        (page_title and BLOCK_PATTERNS.search(page_title.lower()))
    )

    return {
        "page_title": page_title,
        "og_title": og_title,
        "og_site": og_site,
        "slug": slug,
        "domain": parsed.netloc.replace("www.", ""),
        "is_blocked": is_blocked,
    }

# -------------------------
# NORMALIZATION
# -------------------------

def clean_name(text: str | None) -> str | None:
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(by\s+.+)$", "", text, flags=re.I).strip()
    return text

def choose_mod_name(identity: dict) -> str:
    """
    RULES (v3.3):
    - If NOT blocked:
        1. og:title
        2. page <title>
    - If blocked:
        3. slug
    """
    if not identity["is_blocked"]:
        if identity["og_title"]:
            return clean_name(identity["og_title"])
        if identity["page_title"]:
            return clean_name(identity["page_title"])

    # blocked fallback
    return identity["slug"] or "Unknown mod"

def choose_creator(identity: dict) -> str:
    return identity["og_site"] or identity["domain"] or "—"

# -------------------------
# ORCHESTRATOR
# -------------------------

def analyze_url(url: str) -> dict:
    html = fetch_page(url)
    identity = extract_identity(html, url)

    return {
        "url": url,
        "mod_name": choose_mod_name(identity),
        "creator": choose_creator(identity),
        "identity_debug": identity,
    }

# -------------------------
# UI
# -------------------------

st.title("TS4 Mod Analyzer — Phase 1")

st.markdown(
    "Cole a **URL de um mod**.  \n"
    "Esta fase extrai **identidade básica** para evitar duplicatas.  \n"
    "**Não usa LLM.**"
)

url_input = st.text_input(
    "URL do mod",
    placeholder="https://www.patreon.com/..."
)

if st.button("Analisar"):
    if not url_input.strip():
        st.warning("Cole uma URL válida.")
    else:
        with st.spinner("Analisando…"):
            try:
                result = analyze_url(url_input.strip())

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📦 Mod")
                    st.write(result["mod_name"])
                with col2:
                    st.subheader("👤 Criador")
                    st.write(result["creator"])

                if result["identity_debug"]["is_blocked"]:
                    st.warning(
                        "⚠️ Bloqueio detectado (Patreon / CurseForge / Cloudflare). "
                        "Usando slug da URL como fallback."
                    )

                with st.expander("🔍 Debug técnico (Phase 1)", expanded=False):
                    st.json(result["identity_debug"])

                st.success("Identidade extraída.")

            except Exception as e:
                st.error(f"Erro inesperado: {e}")

st.markdown(
    "<div style='text-align:center; opacity:0.6; margin-top:2rem;'>"
    "TS4 Mod Analyzer — v3.3"
    "</div>",
    unsafe_allow_html=True
)
