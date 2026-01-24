# ============================================================
# TS4 Mod Analyzer — Phase 3
# Version: v3.5.0
# Contrato: Log canônico + Cache determinístico + IA controlada
# ============================================================

import streamlit as st
import requests
import hashlib
import json
from datetime import datetime
from urllib.parse import urlparse

# ========================
# CONFIG
# ========================

APP_VERSION = "v3.5.0"

# ========================
# SESSION STATE INIT
# ========================

if "decision_log" not in st.session_state:
    st.session_state.decision_log = []

if "cache" not in st.session_state:
    st.session_state.cache = {}

# ========================
# UTILS
# ========================

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def now() -> str:
    return datetime.utcnow().isoformat()

# ========================
# PHASE 1 — IDENTIDADE
# ========================

def extract_identity(url: str) -> dict:
    parsed = urlparse(url)

    identity = {
        "input_url": url,
        "domain": parsed.netloc.replace("www.", ""),
        "url_slug": parsed.path.strip("/"),
        "extracted_at": now()
    }

    return identity

# ========================
# PHASE 2 — MATCH (determinístico stub)
# ========================

def phase_2_match(identity: dict) -> dict:
    return {
        "status": "WEAK_MATCH",
        "confidence": 0.32,
        "reason": "Slug genérico demais"
    }

# ========================
# PHASE 3 — IA (controlada stub)
# ========================

def phase_3_ai(identity: dict) -> dict:
    return {
        "collapsed": False,
        "confidence": 0.41,
        "reason": "IA não conseguiu colapsar o match"
    }

# ========================
# DECISION ENGINE
# ========================

def analyze(url: str) -> dict:
    identity = extract_identity(url)
    identity_hash = sha256(json.dumps(identity, sort_keys=True))

    # CACHE HIT
    if identity_hash in st.session_state.cache:
        return {
            "from_cache": True,
            "result": st.session_state.cache[identity_hash]
        }

    phase2 = phase_2_match(identity)

    if phase2["status"] == "STRONG_MATCH":
        decision = "FOUND"
        phase3 = None
        final = phase2
    else:
        phase3 = phase_3_ai(identity)
        decision = "NOT_FOUND"
        final = phase3

    log_entry = {
        "timestamp": now(),
        "identity": identity,              # Phase 1 preservada
        "identity_hash": identity_hash,    # Chave determinística
        "phase_2": phase2,
        "phase_3": phase3,
        "decision": decision
    }

    st.session_state.decision_log.append(log_entry)
    st.session_state.cache[identity_hash] = log_entry

    return {
        "from_cache": False,
        "result": log_entry
    }

# ========================
# UI
# ========================

st.set_page_config(
    page_title="TS4 Mod Analyzer — Phase 3",
    layout="wide"
)

st.title("TS4 Mod Analyzer — Phase 3")
st.caption(f"v{APP_VERSION} · IA controlada · Log determinístico")

url = st.text_input("URL do mod")

if st.button("Analisar") and url.strip():
    output = analyze(url.strip())

    if output["from_cache"]:
        st.info("⚡ Resultado vindo do cache")

    result = output["result"]

    st.subheader("📦 Mod")
    st.json(result["identity"])

    st.subheader("🧠 Decisão final")
    st.success(result["decision"])

    with st.expander("🔍 Debug técnico"):
        st.json(result)

# ========================
# CACHE (UX CONTROLADA)
# ========================

st.divider()

with st.expander("🗃️ Cache em memória"):
    st.write(f"Itens no cache: {len(st.session_state.cache)}")
    st.json(list(st.session_state.cache.keys()))

# ========================
# LOG (UX CONTROLADA)
# ========================

st.divider()

with st.expander("📊 Log canônico de decisões"):
    st.write(f"Entradas registradas: {len(st.session_state.decision_log)}")

    for i, entry in enumerate(st.session_state.decision_log, 1):
        with st.expander(f"Decisão #{i} — {entry['decision']}"):
            st.json(entry)

# ========================
# FOOTER (CONTRATO CANÔNICO)
# ========================

st.markdown(
    """
    <div style="text-align:center;padding:1rem 0;font-size:0.85rem;color:#6b7280;">
        <img src="https://64.media.tumblr.com/05d22b63711d2c391482d6faad367ccb/675ea15a79446393-0d/s2048x3072/cc918dd94012fe16170f2526549f3a0b19ecbcf9.png"
             style="height:20px;vertical-align:middle;margin-right:6px;">
        Criado por Akin (@UnpaidSimmer)
        <div style="font-size:0.7rem;opacity:0.6;">
            v3.5.0 · Log canônico · Cache determinístico · IA controlada
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
