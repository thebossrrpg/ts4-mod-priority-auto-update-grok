# No topo do arquivo, logo após os imports, adicione ou confirme:
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

# Substitua a função analyze_url por essa (mais segura)
def analyze_url(url: str) -> dict | None:
    try:
        html = fetch_page(url)
        raw = extract_identity(html, url)
        norm = normalize_identity(raw)
        return {
            "url": url,
            "mod_name": norm["mod_name"],
            "creator": norm["creator"],
            "identity_debug": raw
        }
    except Exception as e:
        st.error(f"Erro na análise completa: {str(e)}")
        return None

# Substitua o bloco inteiro do if st.button("Analisar") por isso:
if st.button("Analisar"):
    if not url_input.strip():
        st.warning("Cole uma URL válida.")
    else:
        with st.spinner("Analisando..."):
            result = analyze_url(url_input.strip())
            if result:
                st.session_state.analysis_result = result
            else:
                st.session_state.analysis_result = None

# Logo abaixo (fora do botão), adicione isso para render persistente:
if st.session_state.analysis_result:
    result = st.session_state.analysis_result

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Mod")
        st.write(result["mod_name"])
    with col2:
        st.subheader("👤 Criador")
        st.write(result["creator"])

    # Botão debug logo após
    if st.button("🔍 Ver debug técnico", help="Detalhes completos da extração", key="debug_btn"):
        with st.expander("Debug técnico (fonte completa)", expanded=True):
            st.json(result["identity_debug"])

    st.success("Identidade extraída!")

    if result["identity_debug"]["is_blocked"]:
        st.warning("⚠️ Bloqueio detectado (Cloudflare ou similar). Usando fallback do slug/domínio.")
    if not result["identity_debug"]["og_title"]:
        st.info("ℹ️ og:title não encontrado. Usando título da página ou slug.")

# ... o resto do código (footer, etc.) permanece igual
