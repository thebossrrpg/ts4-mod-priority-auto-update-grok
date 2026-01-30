# ============================================================
# TS4 Mod Analyzer — Phase 1 → Phase 4 (Hugging Face IA)
# Version: v1.6 — Phase 4 Priority Classification (Closed)
#
# Contract:
# - Phase 1: Identity extraction (URL + HTML)
# - Phase 2: Deterministic Notion match (notioncache)
# - Phase 3: IA as SIGNAL only (never decides)
# - Phase 4: Priority classification (AUTO / MANUAL)
#
# ADDITIVE ONLY — Contract preserved
# ============================================================

import streamlit as st
import requests
import re
import json
import hashlib
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from notion_client import Client
from datetime import datetime, timezone

# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="TS4 Mod Analyzer — Phase 4 · v1.6",
    layout="centered"
)

# =========================
# CONFIG
# =========================

NOTION_TOKEN = st.secrets["notion"]["token"]
NOTION_DATABASE_ID = st.secrets["notion"]["database_id"]

HF_TOKEN = st.secrets["huggingface"]["token"]
HF_MODEL = "https://api-inference.huggingface.co/models/google/flan-t5-base"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

HF_HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

notion = Client(auth=NOTION_TOKEN)

# =========================
# UTILS
# =========================

def now():
    return datetime.now(timezone.utc).isoformat()

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# =========================
# SESSION STATE
# =========================

for key, default in {
    "analysis_result": None,
    "decision_log": [],
    "ai_logs": [],
    "notioncache": {},
    "matchcache": {},
    "phase_4_cache": {},
    "notioncache_loaded": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# =========================
# SNAPSHOT
# =========================

def build_snapshot():
    return {
        "meta": {
            "app": "TS4 Mod Analyzer",
            "version": "v1.6",
            "created_at": now(),
        },
        "phase_2_cache": st.session_state.notioncache,
        "phase_3_cache": st.session_state.matchcache,
        "phase_4_cache": st.session_state.phase_4_cache,
        "canonical_log": st.session_state.decision_log,
    }

# =========================
# PHASE 4 — PROMPT
# =========================

def build_phase4_prompt(notion_page: dict):
    return f"""
You are classifying a Sims 4 mod.

Evaluate the mod using these criteria:

1. Removal / Replacement impact (0–2)
2. Framework dependency importance (0–1)
3. Essential gameplay relevance (0–5)

Rules:
- Total score must be between 0 and 8
- Return JSON only
- Do NOT guess missing info
- Base evaluation ONLY on the provided description

Description:
{notion_page.get("description", "")}

Return format:
{{
  "priority": "0"–"5",
  "subcategory": "optional short label",
  "score": X,
  "source": "AUTO"
}}
"""

# =========================
# PHASE 4 — IA CALL
# =========================

def call_phase4_ai(prompt: str):
    r = requests.post(
        HF_MODEL,
        headers=HF_HEADERS,
        json={"inputs": prompt, "parameters": {"temperature": 0}},
        timeout=60
    )
    data = r.json()
    text = data[0]["generated_text"]
    return json.loads(text)

# =========================
# PHASE 4 — CLASSIFIER
# =========================

def run_phase4(identity_hash: str, notion_page: dict):
    if identity_hash in st.session_state.phase_4_cache:
        return st.session_state.phase_4_cache[identity_hash]

    manual_priority = notion_page.get("priority")
    if manual_priority:
        result = {
            "priority": manual_priority,
            "source": "MANUAL",
            "timestamp": now(),
        }
        st.session_state.phase_4_cache[identity_hash] = result
        return result

    prompt = build_phase4_prompt(notion_page)
    ai_result = call_phase4_ai(prompt)

    if not (0 <= ai_result.get("score", -1) <= 8):
        raise ValueError("Invalid score returned by IA")

    append_note = f"[TS4 AUTO] Subcategoria: {ai_result.get('subcategory')}"

    result = {
        "priority": ai_result["priority"],
        "subcategory": ai_result.get("subcategory"),
        "score": ai_result["score"],
        "source": "AUTO",
        "notes_append": append_note,
        "timestamp": now(),
    }

    st.session_state.phase_4_cache[identity_hash] = result

    st.session_state.ai_logs.append({
        "stage": "PHASE_4",
        "prompt": prompt,
        "result": ai_result,
        "timestamp": now(),
    })

    return result

# =========================
# UI
# =========================

st.title("TS4 Mod Analyzer — Phase 4")
st.caption("Classificação de prioridade · IA como sugestão")

if not st.session_state.notioncache_loaded:
    st.warning("Importe o notioncache para continuar.")
    st.stop()

url = st.text_input("URL do mod")

if st.button("Analisar") and url:
    identity_hash = sha256(url)

    phase3 = st.session_state.matchcache.get(identity_hash)
    if not phase3 or phase3["decision"] != "FOUND":
        st.error("Mod não encontrado no Notion.")
        st.stop()

    notion_page = st.session_state.notioncache["pages"].get(
        phase3["notion_id"]
    )

    phase4 = run_phase4(identity_hash, notion_page)
    st.session_state.analysis_result = phase4

# =========================
# RESULT
# =========================

result = st.session_state.analysis_result
if result:
    st.subheader("📌 Classificação de Prioridade")

    st.markdown(f"**Priority:** {result['priority']}")
    st.markdown(f"**Source:** {result['source']}")

    if result["source"] == "AUTO":
        st.warning("⚠️ Sugestão automática — revisão manual recomendada")
        st.code(result.get("notes_append"))

# =========================
# EXPORT
# =========================

with st.sidebar:
    st.download_button(
        "📸 Snapshot v1.6",
        json.dumps(build_snapshot(), indent=2),
        "snapshot_v1.6.json"
    )
