# ============================================================
# TS4 Mod Analyzer — Phase 2 (Sandbox)
# Version: v3.6.2
# Ironclad end-to-end (nenhum HTTPError derruba o app)
# ============================================================

import streamlit as st
import requests
import re
import os
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# =========================
# CONFIG STREAMLIT
# =========================

st.set_page_config(
    page_title="TS4 Mod Analyzer — Phase 2 (Sandbox)",
    layout="centered"
)

# =========================
# CONFIG GERAL
# =========================

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

STOPWORDS = {
    "mod", "mods", "post", "posts", "v", "v1", "v2", "version",
    "the", "and", "or", "for", "with", "by"
}

# =========================
# NOTION CONFIG
# =========================

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

# =========================
# HELPERS — FASE 1
# =========================

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9+ ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize(text: str) -> list[str]:
    return [
        t for t in clean_text(text).split()
        if t not in STOPWORDS and len(t) > 2
    ]

def fetch_page(url: str) -> str:
    """
    Fase 1 ironclad:
    erro HTTP nunca quebra o app
    """
    try:
        r = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
        return r.text
    except requests.exceptions.RequestException:
        return ""

# =========================
# IDENTIDADE — FASE 1 (ORIGINAL)
# =========================

def extract_identity(html: str, url: str) -> dict:
    parsed = urlparse(url)
    slug = parsed.path.replace("-", " ").replace("/", " ")

    if not html:
        return {
            "mod_name": slug,
            "creator": parsed.netloc.replace("www.", ""),
            "url_slug": slug,
            "domain": parsed.netloc.replace("www.", ""),
            "is_blocked": True
        }

    soup = BeautifulSoup(html, "html.parser")

    page_title = soup.title.string.strip() if soup.title else None

    og_title = None
    og_site = None
    for meta in soup.find_all("meta"):
        if meta.get("property") == "og:title":
            og_title = meta.get("content")
        if meta.get("property") == "og:site_name":
            og_site = meta.get("content")

    blocked = bool(
        page_title
        and "just a moment" in page_title.lower()
    )

    return {
        "mod_name": og_title or page_title or slug,
        "creator": og_site or parsed.netloc.replace("www.", ""),
        "url_slug": slug,
        "domain": parsed.netloc.replace("www.", ""),
        "is_blocked": blocked
    }

# =========================
# NOTION LOOKUP — FASE 2 (IRONCLAD)
# =========================

def query_notion(identity: dict, limit: int = 3) -> list[dict]:
    """
    Lookup real no Notion.
    Nunca levanta exceção.
    Retorna até 3 candidatos ou lista vazia.
    """

    tokens = tokenize(identity["mod_name"]) + tokenize(identity["url_slug"])
    search_text = " ".join(tokens[:5])

    url = f"{NOTION_API_URL}/databases/{NOTION_DATABASE_ID}/query"

    payload = {
        "page_size": 10,
        "filter": {
            "or": [
                {
                    "property": "Name",
                    "title": {"contains": search_text}
                },
                {
                    "property": "Source URL",
                    "url": {"contains": identity["domain"]}
                }
            ]
        }
    }

    try:
        r = requests.post(
            url,
            headers=NOTION_HEADERS,
            json=payload,
            timeout=20
        )
        data = r.json()
    except Exception:
        return []

    pages = data.get("results", [])
    candidates = []

    for page in pages[:limit]:
        props = page.get("properties", {})

        title = "(sem título)"
        if props.get("Name", {}).get("title"):
            title = props["Name"]["title"][0]["plain_text"]

        category = props.get("Category", {}).get("select", {})
        priority = props.get("Priority", {}).get("select", {})

        candidates.append({
            "title": title,
            "category": category.get("name") if category else None,
            "priority": priority.get("name") if priority else None,
            "url": page.get("url"),
            "reason": "Match por nome / domínio"
        })

    return candidates

def phase2(identity: dict) -> dict:
    candidates = query_notion(identity)
    count = len(candidates)

    if count == 0:
        status = "new_entry"
    elif count == 1:
        status = "unique_match"
    elif count <= 3:
        status = "ambiguous"
    else:
        status = "too_ambiguous"

    return {
        "status": status,
        "candidates_found": count,
        "candidates": candidates
    }

# =========================
# UI
# =========================

st.title("🧪 Fase 2 (Sandbox): verificação no Notion")
st.caption("⚠️ Read-only · até 3 possibilidades · sem decisão automática")

url = st.text_input("URL do mod")

if st.button("Analisar") and url.strip():
    with st.spinner("Analisando..."):
        html = fetch_page(url)
        identity = extract_identity(html, url)
        phase2_result = phase2(identity)

    st.subheader("📦 Identidade detectada")
    st.write(f"**Mod:** {identity['mod_name']}")
    st.write(f"**Criador:** {identity['creator']}")
    st.write(f"**Domínio:** {identity['domain']}")

    if identity["is_blocked"]:
        st.warning("⚠️ Página bloqueou leitura automática. Identidade baseada na URL.")

    st.subheader("🔎 Resultado da Fase 2")
    st.write("**Status:**", phase2_result["status"])
    st.write("**Candidatos encontrados:**", phase2_result["candidates_found"])

    if phase2_result["candidates_found"] > 0:
        for c in phase2_result["candidates"]:
            st.markdown(
                f"- **[{c['title']}]({c['url']})**  \n"
                f"  Categoria: {c['category'] or '—'} · "
                f"Prioridade: {c['priority'] or '—'}  \n"
                f"  Motivo: _{c['reason']}_"
            )
    else:
        st.success("Nenhuma entrada correspondente encontrada no Notion.")

    with st.expander("🔍 Debug completo"):
        st.json({
            "identity": identity,
            "phase2": phase2_result
        })

# =========================
# FOOTER (RESTAURADO)
# =========================

st.markdown(
    """
    <div style="text-align: center; padding: 1rem 0; font-size: 0.9rem; color: #6b7280;">
        <img src="https://64.media.tumblr.com/05d22b63711d2c391482d6faad367ccb/675ea15a79446393-0d/s2048x3072/cc918dd94012fe16170f2526549f3a0b19ecbcf9.png" 
             alt="Favicon" 
             style="height: 20px; vertical-align: middle; margin-right: 8px;">
        Criado por Akin (@UnpaidSimmer) · v3.6.2 · Sandbox
        <div style="margin-top: 0.5rem; font-size: 0.75rem; opacity: 0.6;">
            v3.5 lineage
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
