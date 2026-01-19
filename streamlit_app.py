# ==========================================================
# TS4 Mod Priority Auto Update
# Phase 2 – Sandbox (Baseline duplicate detection)
# Version: v3.4
# ==========================================================

import streamlit as st
import requests
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

# ----------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------

st.set_page_config(
    page_title="TS4 Mod Priority – Fase 2 (Sandbox)",
    layout="centered",
)

# ----------------------------------------------------------
# SESSION STATE INIT
# ----------------------------------------------------------

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# ----------------------------------------------------------
# UTILS
# ----------------------------------------------------------

def tokenize(text: str) -> set[str]:
    """
    Tokenização tolerante:
    - mantém siglas (lgbtqia+)
    - remove lixo
    - ignora tokens muito curtos
    """
    if not text:
        return set()

    tokens = re.findall(r"[a-zA-Z0-9\+]+", text.lower())
    return {t for t in tokens if len(t) >= 3}


def compute_similarity_baseline(slug: str, notion_name: str) -> dict:
    """
    Score base determinístico.
    GARANTE score > 0 se houver interseção semântica mínima.
    """

    slug_tokens = tokenize(slug)
    notion_tokens = tokenize(notion_name)

    common_tokens = slug_tokens & notion_tokens

    debug = {
        "slug_tokens": sorted(slug_tokens),
        "notion_tokens": sorted(notion_tokens),
        "common_tokens": sorted(common_tokens),
    }

    # REGRA DE OURO
    if common_tokens:
        intersection_score = len(common_tokens) / max(
            len(slug_tokens), len(notion_tokens)
        )

        score = max(0.15, intersection_score)

        debug["reason"] = "token_intersection"
        debug["raw_intersection_score"] = intersection_score

        return {
            "score": round(score, 2),
            "debug": debug,
        }

    # fallback fuzzy fraco
    fuzzy_score = SequenceMatcher(
        None,
        slug.lower(),
        notion_name.lower()
    ).ratio()

    debug["reason"] = "fuzzy_fallback"

    return {
        "score": round(fuzzy_score * 0.3, 2),
        "debug": debug,
    }


def extract_identity(url: str) -> dict:
    """
    Identidade mínima (igual Fase 1).
    """
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")

    slug = parsed.path.replace("/", " ").replace("-", " ").strip()

    return {
        "mod_name": slug.title() if slug else "Desconhecido",
        "creator": domain,
        "url_slug": slug.lower(),
        "domain": domain,
    }


# ----------------------------------------------------------
# UI
# ----------------------------------------------------------

st.title("🧪 Fase 2 (Sandbox): detecção de duplicatas")
st.caption("⚠️ Não escreve no Notion. Apenas testes de score.")

url_input = st.text_input("URL do mod")

if st.button("Analisar"):
    if not url_input.strip():
        st.warning("Cole uma URL válida.")
    else:
        identity = extract_identity(url_input.strip())

        # 🔴 MOCK de nomes do Notion (sandbox)
        # depois isso vira query real
        notion_candidates = [
            "LGBTQIA+ / Gender & Orientation Overhaul",
            "Mini-mods: Tweaks & Changes",
            "Automatic Beard Shadows",
        ]

        scores = []

        for notion_name in notion_candidates:
            baseline = compute_similarity_baseline(
                slug=identity["url_slug"],
                notion_name=notion_name
            )

            scores.append({
                "notion_name": notion_name,
                "score": baseline["score"],
                "debug": baseline["debug"],
            })

        best_match = max(scores, key=lambda x: x["score"])

        st.session_state.analysis_result = {
            "identity": identity,
            "scores": scores,
            "best_match": best_match,
        }

# ----------------------------------------------------------
# RENDER RESULT
# ----------------------------------------------------------

result = st.session_state.analysis_result

if result:
    st.divider()

    st.subheader("📦 Identidade")
    st.write(f"**Mod:** {result['identity']['mod_name']}")
    st.write(f"**Criador:** {result['identity']['creator']}")

    st.subheader("🔎 Verificação de duplicata")

    score = result["best_match"]["score"]

    if score >= 0.6:
        st.error("🚨 Provável duplicata")
    elif score >= 0.15:
        st.warning("⚠️ Possível match (ambíguo)")
    else:
        st.success("✅ Provavelmente novo mod")

    st.write(f"**Score:** {score}")
    st.write(f"**Possível match:** {result['best_match']['notion_name']}")

    with st.expander("🔍 Debug detalhado"):
        st.json(result)

st.divider()

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
