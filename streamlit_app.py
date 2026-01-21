# ============================================================
# TS4 Mod Analyzer — Phase 1 → Phase 3 (IA Assistida)
# Version: v3.4.8
#
# Patch:
# - Correção de loop no startup (bloqueio da API Notion)
# ============================================================

import streamlit as st
import requests
import re
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from notion_client import Client
from rapidfuzz import fuzz

from cohere_provider import CohereProvider

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="TS4 Mod Analyzer — Phases 1–3 · v3.4.8",
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
# NOTION
# =========================

NOTION_TOKEN = st.secrets["notion"]["token"]
NOTION_DATABASE_ID = st.secrets["notion"]["database_id"]
notion = Client(auth=NOTION_TOKEN)

# =========================
# CACHE — BASE NOTION
# =========================

@st.cache_data(show_spinner=False)
def load_notion_index():
    results = []
    cursor = None

    while True:
        payload = {
            "database_id": NOTION_DATABASE_ID,
            "page_size": 100
        }
        if cursor:
            payload["start_cursor"] = cursor

        try:
            r = notion.databases.query(**payload)
        except Exception:
            break  # ⬅️ correção cirúrgica do loop

        for p in r["results"]:
            title_prop = p["properties"]["Filename"]["title"]
            if title_prop:
                results.append({
                    "id": p["id"],
                    "title": title_prop[0]["plain_text"]
                })

        if not r.get("has_more"):
            break
        cursor = r.get("next_cursor")

    return results


@st.cache_data(show_spinner=False)
def get_notion_index():
    return load_notion_index()

# =========================
# FETCH
# =========================

@st.cache_data(show_spinner=False)
def fetch_page(url: str) -> str:
    try:
        r = requests.get(url, headers=REQUEST_HEADERS, timeout=25)
        return r.text or ""
    except Exception:
        return ""

# =========================
# PHASE 1 — EXTRACTION
# =========================

def extract_identity(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    page_title = soup.title.get_text(strip=True) if soup.title else None
    og_title = None

    for meta in soup.find_all("meta"):
        if meta.get("property") == "og:title":
            og_title = meta.get("content", "").strip()

    parsed = urlparse(url)
    slug = parsed.path.strip("/").replace("-", " ").replace("/", " ").strip()

    blocked = bool(
        re.search(r"(just a moment|cloudflare|checking your browser)", html.lower())
    )

    return {
        "page_title": page_title,
        "og_title": og_title,
        "url_slug": slug,
        "domain": parsed.netloc.replace("www.", ""),
        "is_blocked": blocked
    }

# =========================
# NORMALIZAÇÃO + ENTIDADES
# =========================

def normalize_name(raw: str) -> str:
    if not raw:
        return ""
    raw = re.sub(r"(the sims resource\s*\|\s*)", "", raw, flags=re.I)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()

def extract_entities(debug: dict) -> dict:
    title = normalize_name(debug.get("og_title") or debug.get("page_title") or "")

    creator = None
    m = re.search(r"(.+?)'?s\s", title)
    if m:
        creator = m.group(1)
        title = title.replace(m.group(0), "").strip()

    return {
        "extracted_title": title or None,
        "extracted_creator": creator,
        "slug_quality": "poor" if len(debug.get("url_slug", "")) < 6 else "ok",
        "page_blocked": debug.get("is_blocked")
    }

# =========================
# PHASE 2 — FUZZY MATCH
# =========================

def search_notion_fuzzy(title: str, notion_index: list, threshold=70):
    if not title:
        return []

    matches = []
    for p in notion_index:
        score = fuzz.token_set_ratio(title.lower(), p["title"].lower())
        if score >= threshold:
            matches.append({
                "id": p["id"],
                "title": p["title"],
                "score": score
            })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:5]

# =========================
# FOOTER (INTOCADO)
# =========================

st.markdown(
    """
    <div style="text-align: center; padding: 1rem 0; font-size: 0.9rem; color: #6b7280;">
        <img src="https://64.media.tumblr.com/05d22b63711d2c391482d6faad367ccb/675ea15a79446393-0d/s2048x3072/cc918dd94012fe16170f2526549f3a0b19ecbcf9.png"
             style="height: 20px; vertical-align: middle; margin-right: 8px;">
        Criado por Akin (@UnpaidSimmer)
        <div style="margin-top: 0.5rem; font-size: 0.75rem; opacity: 0.6;">
            v3.4.8 · Phase 3 IA assistida · Cohere
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
