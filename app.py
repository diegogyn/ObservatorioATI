import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import re
import io

# ================================
# Configuração da Página
# ================================
st.set_page_config(page_title="Observatório ATI", page_icon="💻", layout="wide")

# ================================
# DESIGN SYSTEM (CSS & Layout)
# ================================
def apply_design_system():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }

        /* Estilo dos Metric Cards (KPIs) */
        [data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 1.2rem;
            border-radius: 0.75rem;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        }

        /* Dark mode automático */
        @media (prefers-color-scheme: dark) {
            [data-testid="stMetric"] {
                background-color: #1e293b;
                border-color: #334155;
            }
        }

        /* Estilo da tabela de dados */
        [data-testid="stDataFrame"] {
            border-radius: 0.5rem;
            overflow: hidden;
        }

        /* Melhoria visual dos expanders */
        [data-testid="stExpander"] {
            border-radius: 0.5rem;
            border: 1px solid #e2e8f0;
        }
        </style>
    """, unsafe_allow_html=True)


# Cores do Design System
CORES = {
    "brand_main":    "#2563eb",
    "brand_light":   "#93c5fd",
    "brand_dark":    "#1e3a8a",
    "ink_main":      "#64748b",
    "ink_light":     "#cbd5e1",
    "red_alert":     "#ef4444",
    "green_success": "#10b981",
    "purple_alt":    "#8b5cf6",
    "gray_empty":    "#94a3b8",
}


def apply_plotly_layout(fig):
    """Aplica layout padrão do Design System a qualquer figura Plotly."""
    fig.update_layout(
        font_family="Inter",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=20, l=10, r=10),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(100, 116, 139, 0.1)", zeroline=False)
    return fig


# ================================
# CARREGAMENTO DE DADOS
# ================================
@st.cache_data
def load_data():
    caminho_arquivo      = os.path.join("data", "dados_atis.csv")
    caminho_meta         = os.path.join("data", "metadata.json")
    caminho_desligamentos = os.path.join("data", "desligamentos-ati-pep-fev-2026.csv")

    # Data de referência
    data_ref = "Atualização Pendente"
    if os.path.exists(caminho_meta):
        with open(caminho_meta, "r", encoding="utf-8") as f:
            data_ref = json.load(f).get("data_referencia", "Desconhecida")

    # Base principal
    try:
        df = pd.read_csv(caminho_arquivo)
    except FileNotFoundError:
        df = pd.DataFrame()

    if not df.empty:
        # Classe (A, B, C, Especial)
        df["Classe"] = df["Nível/Padrão"].apply(
            lambda x: str(x).split("-")[0].strip().upper() if pd.notna(x) else "Desconhecida"
        )

        # Parse de datas de ingresso
        df["Data Ingresso Servico"] = pd.to_datetime(
            df["Ingresso Serviço Público"], format="%d/%m/%Y", errors="coerce"
        )
        df["Ano de Ingresso"] = (
            df["Data Ingresso Servico"]
            .dt.year
            .fillna(0)
            .astype(int)
            .astype(str)
            .replace("0", "Desconhecido")
        )

        # Classificação estratégica das Funções (FCE)
        def classificar_funcao(funcao):
            funcao_str = str(funcao).strip().upper()
            if funcao_str in {"SEM FUNÇÃO", "NAN", ""}:
                return "Sem Função", "Sem Função", "Sem Função", -1

            match = re.search(r"\b(FCE)\b.*?(?:[^\d]|^)(\d{2})\b", funcao_str)
            if match:
                nivel = match.group(2)
                if nivel.isdigit() and 1 <= int(nivel) <= 17:
                    return f"FCE Nível {nivel}", "FCE", f"Nível {nivel}", int(nivel)

            return "Outras Funções", "Outras Funções", "Outras", 0

        if "Função" in df.columns:
            resultados = df["Função"].apply(classificar_funcao)
            df["Função Resumo"] = [r[0] for r in resultados]
            df["Tipo Função"]   = [r[1] for r in resultados]
            df["Nível Função"]  = [r[2] for r in resultados]
            df["Ordem Nível"]   = [r[3] for r in resultados]
        else:
            df[["Função Resumo", "Tipo Função", "Nível Função"]] = "Desconhecida"
            df["Ordem Nível"] = -1

    # Base de desligamentos
    try:
        df_deslig = pd.read_csv(caminho_desligamentos, encoding="utf-8-sig")
        df_deslig = df_deslig[df_deslig["Ano"].astype(str).str.isnumeric()].copy()
        df_deslig = df_deslig.rename(columns={"Quantidade de Desligamentos": "Desligamentos"})
        df_deslig["Ano"]           = df_deslig["Ano"].astype(str)
        df_deslig["Desligamentos"] = df_deslig["Desligamentos"].astype(int)
        df_deslig = df_deslig[["Ano", "Desligamentos"]]
    except FileNotFoundError:
        df_deslig = pd.DataFrame(columns=["Ano", "Desligamentos"])

    return df, data_ref, df_deslig


# ──────────────────────────────────────────────
apply_design_system()
df, data_ref, df_deslig = load_data()

# ================================
# MENU LATERAL
# ================================
pagina = st.sidebar.radio("📌 Navegação do Painel", ["📊 Observatório ATI", "📚 Sobre a Carreira"])
st.sidebar.divider()


# ════════════════════════════════════════════════
# PÁGINA 1 — OBSERVATÓRIO
# ════════════════════════════════════════════════
if pagina == "📊 Observatório ATI":

    st.markdown("<h1 style='color: #0f172a;'>💻 Observatório da Carreira ATI</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color: #64748b; font-size: 1.1rem;'>Painel interativo com a distribuição dos "
        "<b>Analistas em Tecnologia da Informação</b> do Executivo Federal.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    if df.empty:
        st.warning("⚠️ Dados não encontrados. Verifique a base de dados na pasta 'data'.")
        st.stop()

    # ── FILTROS ──────────────────────────────────
    st.sidebar.markdown(f"**📅 Mês de Referência:**\n\n*{data_ref}*")
    st.sidebar.header("🔍 Filtros do Painel")

    orgaos = ["Todos"] + sorted(df["Órgão de Exercício"].dropna().unique())
    orgao_selecionado = st.sidebar.selectbox("Órgão de Exercício:", orgaos)

    funcao_selecionada = st.sidebar.radio(
        "Ocupa Função Comissionada?", ["Todos", "Sim", "Não"]
    )

    classes = ["Todas"] + sorted(
        df[df["Classe"] != "Desconhecida"]["Classe"].unique()
    )
    classe_selecionada = st.sidebar.selectbox("Classe na Carreira:", classes)

    anos_validos = sorted(
        [a for a in df["Ano de Ingresso"].unique() if str(a).isdigit()], reverse=True
    )
    ano_selecionado = st.sidebar.selectbox("Ano de Ingresso:", ["Todos"] + anos_validos)

    # ── APLICAÇÃO DOS FILTROS ─────────────────────
    df_filtrado = df.copy()
    if orgao_selecionado  != "Todos":  df_filtrado = df_filtrado[df_filtrado["Órgão de Exercício"] == orgao_selecionado]
    if funcao_selecionada != "Todos":  df_filtrado = df_filtrado[df_filtrado["Tem Função?"]        == funcao_selecionada]
    if classe_selecionada != "Todas":  df_filtrado = df_filtrado[df_filtrado["Classe"]             == classe_selecionada]
    if ano_selecionado    != "Todos":  df_filtrado = df_filtrado[df_filtrado["Ano de Ingresso"]    == ano_selecionado]

    # ── KPIs ──────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    total = len(df_filtrado)

    with col1:
        st.metric("Total de ATIs (Filtro)", total)

    with col2:
        # FIX: evita divisão por zero com operador ternário seguro
        atis_func = len(df_filtrado[df_filtrado["Tem Função?"] == "Sim"]) if total > 0 else 0
        perc = (atis_func / total * 100) if total > 0 else 0
        st.metric("Com Função", f"{atis_func} ({perc:.0f}%)")

    with col3:
        st.metric("Órgãos Distintos", df_filtrado["Órgão de Exercício"].nunique())

    with col4:
        # FIX: trata DataFrame vazio antes de chamar .mode()
        if not df_filtrado.empty and df_filtrado["Ano de Ingresso"].notna().any():
            ano_mais_comum = df_filtrado["Ano de Ingresso"].mode().iloc[0]
        else:
            ano_mais_comum = "-"
        st.metric("Ano de Ingresso (Moda)", ano_mais_comum)

    st.divider()

    # ── GRÁFICOS PARTE 1 ──────────────────────────
    colA, colB = st.columns(2)

    with colA:
        st.subheader("🏢 Top 10 Órgãos com mais ATIs")
        if not df_filtrado.empty:
            top_10_nomes = df_filtrado["Órgão de Exercício"].value_counts().head(10).index.tolist()
            df_top10 = df_filtrado[df_filtrado["Órgão de Exercício"].isin(top_10_nomes)]
            df_orgaos_func = (
                df_top10
                .groupby(["Órgão de Exercício", "Tem Função?"])
                .size()
                .reset_index(name="Quantidade")
            )
            fig_orgaos = px.bar(
                df_orgaos_func,
                x="Quantidade",
                y="Órgão de Exercício",
                color="Tem Função?",
                orientation="h",
                color_discrete_map={"Sim": CORES["brand_main"], "Não": CORES["ink_light"]},
                category_orders={"Órgão de Exercício": top_10_nomes[::-1]},
                labels={"Tem Função?": "Função"},
            )
            fig_orgaos.update_layout(barmode="stack", yaxis_title="", xaxis_title="Quantidade de ATIs")
            st.plotly_chart(apply_plotly_layout(fig_orgaos), use_container_width=True)
        else:
            st.info("Sem dados para exibir com os filtros selecionados.")

    with colB:
        st.subheader("📊 Distribuição por Nível/Padrão")
        if not df_filtrado.empty:
            df_niveis = (
                df_filtrado
                .groupby(["Nível/Padrão", "Tem Função?"])
                .size()
                .reset_index(name="Quantidade")
                .sort_values("Nível/Padrão")
            )
            fig_niveis = px.bar(
                df_niveis,
                x="Nível/Padrão",
                y="Quantidade",
                color="Tem Função?",
                color_discrete_map={"Sim": CORES["brand_main"], "Não": CORES["ink_light"]},
                labels={"Tem Função?": "Função"},
            )
            fig_niveis.update_layout(
                barmode="stack",
                xaxis_title="Padrão na Carreira",
                yaxis_title="Servidores",
            )
            st.plotly_chart(apply_plotly_layout(fig_niveis), use_container_width=True)
        else:
            st.info("Sem dados para exibir com os filtros selecionados.")

    st.divider()

    # ── GRÁFICOS PARTE 2 ──────────────────────────
    colC, colD = st.columns(2)

    with colC:
        st.subheader("⏳ Histórico de Ingresso")
        df_anos = df_filtrado[df_filtrado["Ano de Ingresso"] != "Desconhecido"]
        if not df_anos.empty:
            df_ingressos = (
                df_anos
                .groupby("Ano de Ingresso")
                .size()
                .reset_index(name="Quantidade")
                .sort_values("Ano de Ingresso")
            )
            fig_anos = px.line(
                df_ingressos,
                x="Ano de Ingresso",
                y="Quantidade",
                markers=True,
                text="Quantidade",
                color_discrete_sequence=[CORES["brand_main"]],
            )
            fig_anos.update_traces(textposition="top center")
            fig_anos.update_layout(xaxis_title="Ano", yaxis_title="Ingressos")
            st.plotly_chart(apply_plotly_layout(fig_anos), use_container_width=True)
        else:
            st.info("Sem dados de ingresso disponíveis.")

    with colD:
        st.subheader("📈 Proporção de Funções por Classe")
        df_classes_func = df_filtrado[df_filtrado["Classe"] != "Desconhecida"]
        if not df_classes_func.empty:
            df_cf = (
                df_classes_func
                .groupby(["Classe", "Tem Função?"])
                .size()
                .reset_index(name="Quantidade")
            )
            fig_classes = px.bar(
                df_cf,
                x="Classe",
                y="Quantidade",
                color="Tem Função?",
                color_discrete_map={"Sim": CORES["brand_main"], "Não": CORES["ink_light"]},
                category_orders={"Classe": ["A", "B", "C", "ESPECIAL"]},
                labels={"Tem Função?": "Função"},
            )
            fig_classes.update_layout(
                barmode="group",
                xaxis_title="Classe",
                yaxis_title="Servidores",
            )
            st.plotly_chart(apply_plotly_layout(fig_classes), use_container_width=True)
        else:
            st.info("Sem dados de classe disponíveis.")

    # ── RAIO-X DAS FUNÇÕES (FCE) ──────────────────
    st.divider()
    st.subheader("🎯 Raio-X das Funções Comissionadas Executivas (FCE)")
    st.markdown(
        "<p style='color: #64748b;'>Visão detalhada sobre o nível de chefia e assessoramento "
        "ocupado pelos servidores. As funções estão agrupadas pelo seu nível oficial "
        "(ex: FCE 1.13 está no Nível 13).</p>",
        unsafe_allow_html=True,
    )

    col_Dnt, col_Bar = st.columns([1, 2])
    cores_map_fce = {
        "FCE":             CORES["green_success"],
        "Outras Funções":  CORES["purple_alt"],
        "Sem Função":      CORES["gray_empty"],
    }

    with col_Dnt:
        # FIX: inclui apenas quem TEM função (FCE + Outras) no donut
        df_com_funcao = df_filtrado[df_filtrado["Tipo Função"] != "Sem Função"]
        if not df_com_funcao.empty:
            df_pizza = df_com_funcao["Tipo Função"].value_counts().reset_index()
            df_pizza.columns = ["Tipo", "Quantidade"]
            fig_pizza = px.pie(
                df_pizza,
                values="Quantidade",
                names="Tipo",
                hole=0.45,
                color="Tipo",
                color_discrete_map=cores_map_fce,
                title="Distribuição das Funções",
            )
            fig_pizza.update_traces(textposition="inside", textinfo="percent+label")
            fig_pizza.update_layout(
                showlegend=False,
                margin=dict(t=40, b=20, l=0, r=0),
                font_family="Inter",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.info("Sem dados de função para exibir.")

    with col_Bar:
        df_fce = df_filtrado[df_filtrado["Tipo Função"] == "FCE"]
        if not df_fce.empty:
            df_bar = (
                df_fce
                .groupby(["Nível Função", "Ordem Nível"])
                .size()
                .reset_index(name="Quantidade")
                .sort_values("Ordem Nível")
            )
            fig_bar = px.bar(
                df_bar,
                x="Nível Função",
                y="Quantidade",
                text="Quantidade",
                color_discrete_sequence=[CORES["green_success"]],
                title="Quantidade de ATIs por Nível FCE",
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(xaxis_title="Nível FCE", yaxis_title="Quantidade de Servidores")
            st.plotly_chart(apply_plotly_layout(fig_bar), use_container_width=True)
        else:
            st.info("Nenhum servidor FCE no filtro atual.")

    # ── BALANÇO DA CARREIRA ───────────────────────
    st.divider()
    st.subheader("⚖️ Balanço da Carreira — Ingressos vs. Evasão")
    st.markdown(
        "<p style='color: #64748b;'>Comparativo histórico entre a entrada de novos servidores e a "
        "perda por desligamentos. Representa o <b>cenário geral</b> e não sofre alteração dos filtros laterais.</p>",
        unsafe_allow_html=True,
    )

    if not df_deslig.empty:
        # FIX: usa a base completa (df), não a filtrada
        df_ingressos_global = (
            df[df["Ano de Ingresso"] != "Desconhecido"]
            .groupby("Ano de Ingresso")
            .size()
            .reset_index(name="Ingressos")
            .rename(columns={"Ano de Ingresso": "Ano"})
        )

        df_balanco = (
            pd.merge(df_ingressos_global, df_deslig, on="Ano", how="outer")
            .fillna(0)
        )
        df_balanco[["Ingressos", "Desligamentos"]] = df_balanco[["Ingressos", "Desligamentos"]].astype(int)

        # FIX: filtro de ano robusto (evita erro em valores não numéricos residuais)
        df_balanco = df_balanco[pd.to_numeric(df_balanco["Ano"], errors="coerce").fillna(0) >= 2010]
        df_balanco = df_balanco.sort_values("Ano")

        total_ingressos     = df_balanco["Ingressos"].sum()
        total_desligamentos = df_balanco["Desligamentos"].sum()
        taxa_evasao         = (total_desligamentos / total_ingressos * 100) if total_ingressos > 0 else 0

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Ingressos (Desde 2010)",        total_ingressos)
        with col_m2:
            st.metric("Desligamentos (Desde 2010)",    total_desligamentos)
        with col_m3:
            st.metric("Taxa de Evasão",                f"{taxa_evasao:.1f}%")

        st.write("")

        df_melted = df_balanco.melt(
            id_vars="Ano",
            value_vars=["Ingressos", "Desligamentos"],
            var_name="Movimentação",
            value_name="Quantidade",
        )
        fig_balanco = px.bar(
            df_melted,
            x="Ano",
            y="Quantidade",
            color="Movimentação",
            barmode="group",
            color_discrete_map={
                "Ingressos":      CORES["brand_main"],
                "Desligamentos":  CORES["red_alert"],
            },
            text_auto=True,
        )
        fig_balanco.update_traces(textposition="outside")
        fig_balanco.update_layout(
            yaxis_title="Qtd. de Servidores",
            xaxis_title="Ano do Evento",
        )
        st.plotly_chart(apply_plotly_layout(fig_balanco), use_container_width=True)

        st.markdown(f"""
        <div style="background-color: #fef2f2; border-left: 4px solid {CORES['red_alert']};
                    padding: 1rem; border-radius: 0.5rem; margin-top: 1rem;">
            <strong style="color: #991b1b;">⚠️ Importante:</strong>
            <span style="color: #7f1d1d;">Os dados consideram apenas ATIs que assumiram e depois saíram;
            a evasão real é maior ao incluir aprovados que não tomaram posse.</span>
            <br><br>
            <span style="color: #7f1d1d;">Isso compromete a <b>Estratégia de Governo Digital</b>
            e gera impactos diretos:</span>
            <ul style="color: #7f1d1d; margin-top: 0.5rem; margin-bottom: 0;">
                <li><b>Custos elevados e dependência:</b> aumento da terceirização e menor capacidade de fiscalização técnica.</li>
                <li><b>Perda de conhecimento:</b> evasão contínua gera retrabalho e ineficiência.</li>
                <li><b>Atraso na inovação:</b> projetos estratégicos sofrem com falta de liderança técnica.</li>
                <li><b>Riscos à segurança:</b> maior exposição a incidentes e perda de soberania sobre dados.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Nenhum dado de evasão encontrado. Adicione o arquivo de desligamentos na pasta 'data'.")

    # ── TABELA FINAL ──────────────────────────────
    st.divider()
    st.subheader("📋 Base de Dados Completa")

    # FIX: lista explícita e segura das colunas internas a ocultar
    colunas_ocultar = ["Data Ingresso Servico", "Ordem Nível", "Tipo Função", "Nível Função"]
    colunas_exibir  = [c for c in df_filtrado.columns if c not in colunas_ocultar]
    st.dataframe(df_filtrado[colunas_exibir], use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════
# PÁGINA 2 — SOBRE A CARREIRA
# ════════════════════════════════════════════════
elif pagina == "📚 Sobre a Carreira":

    st.markdown("<h1 style='color: #0f172a;'>📚 Carreira ATI</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color: #64748b; font-size: 1.1rem;'>Lei nº 14.875, de 31 de maio de 2024 · Guia da carreira de Analista em Tecnologia da Informação.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    with st.expander("🖥️ O que faz o ATI?", expanded=True):
        st.markdown("""
O **Analista em Tecnologia da Informação (ATI)** é um cargo do Poder Executivo Federal voltado para a
**gestão estratégica e governança de Tecnologia da Informação** no governo.

O profissional atua em áreas como:
- Planejamento, coordenação e supervisão dos recursos de TI nos órgãos federais
- Formulação e apoio a políticas de TI
- Gestão de sistemas e infraestrutura tecnológica
- Governança de dados e segurança da informação
- Transformação digital do Estado e inovação dos serviços públicos
        """)

    with st.expander("💰 Como funciona a remuneração?"):
        st.markdown("""
A remuneração é estruturada no modelo de **subsídio** — parcela única mensal, sem gratificações incorporadas.

Verbas indenizatórias adicionais:
- Auxílio-alimentação
- Auxílio-transporte
- Auxílio-saúde
- Auxílio pré-escolar
- 13º salário
- 1/3 constitucional de férias
        """)
        st.link_button("💰 Simulador de Salário dos ATIs",
                       "https://josebarbosa.com.br/simuladores/executivofederal/")

    with st.expander("📈 Como funciona a progressão na carreira?"):
        st.markdown("""
### Progressão Funcional
Passagem de um **padrão para o seguinte dentro da mesma classe** (ex: A-I → A-II).

**Lei nº 14.875/2024:** interstício mínimo de **12 meses**.

**Situação atual (2026):**
- **18 meses** — servidores sem função comissionada
- **12 meses** — servidores ocupando função comissionada

---

### Promoção
Passagem do **último padrão de uma classe para o primeiro da seguinte** (ex: A-V → B-I).

**Lei nº 14.875/2024:** interstício mínimo de **12 meses** no último padrão.

**Situação atual (2026):** mesmas regras transitórias da progressão.
        """)

    with st.expander("🏛️ Requisitos para promoção (mudança de classe)"):
        st.markdown("""
**Art. 36 da Lei nº 14.875/2024** — a promoção ocorre com cumprimento simultâneo de:

1. Interstício mínimo no último padrão da classe atual
2. Avaliação de desempenho com resultado **satisfatório**
        """)

    with st.expander("💼 Valores Oficiais (FCE)"):
        st.markdown("Tabelas exatas de remuneração da **Função Comissionada Executiva (FCE)**.")

        dados_raw_fce = """Cargo/Função\tValor\tCCE Unitário
FCE 1 17\tR$ 16.765,90\t4,79
FCE 1 16\tR$ 14.045,67\t4,01
FCE 1 15\tR$ 12.196,47\t3,49
FCE 1 14\tR$ 10.432,37\t2,98
FCE 1 13\tR$ 8.651,81\t2,47
FCE 1 12\tR$ 6.513,87\t1,86
FCE 1 11\tR$ 5.193,87\t1,48
FCE 1 10\tR$ 4.455,87\t1,27
FCE 1 09\tR$ 3.498,47\t1,00
FCE 1 08\tR$ 3.356,01\t0,96
FCE 1 07\tR$ 2.908,64\t0,83
FCE 1 06\tR$ 2.463,00\t0,70
FCE 1 05\tR$ 2.099,09\t0,60
FCE 1 04\tR$ 1.553,73\t0,44
FCE 1 03\tR$ 1.294,43\t0,37
FCE 1 02\tR$ 723,98\t0,21
FCE 1 01\tR$ 428,38\t0,12
FCE 2 17\tR$ 16.765,90\t4,79
FCE 2 16\tR$ 14.045,67\t4,01
FCE 2 15\tR$ 12.196,47\t3,49
FCE 2 14\tR$ 10.432,37\t2,98
FCE 2 13\tR$ 8.651,81\t2,47
FCE 2 12\tR$ 6.513,87\t1,86
FCE 2 11\tR$ 5.193,87\t1,48
FCE 2 10\tR$ 4.455,87\t1,27
FCE 2 09\tR$ 3.498,47\t1,00
FCE 2 08\tR$ 3.356,01\t0,96
FCE 2 07\tR$ 2.908,64\t0,83
FCE 2 06\tR$ 2.463,00\t0,70
FCE 2 05\tR$ 2.099,09\t0,60
FCE 2 04\tR$ 1.553,73\t0,44
FCE 2 03\tR$ 1.294,43\t0,37
FCE 2 02\tR$ 723,98\t0,21
FCE 2 01\tR$ 428,38\t0,12
FCE 3 16\tR$ 14.045,67\t4,01
FCE 3 15\tR$ 12.196,47\t3,49
FCE 3 14\tR$ 10.432,37\t2,98
FCE 3 13\tR$ 8.651,81\t2,47
FCE 3 12\tR$ 6.513,87\t1,86
FCE 3 11\tR$ 5.193,87\t1,48
FCE 3 10\tR$ 4.455,87\t1,27
FCE 3 09\tR$ 3.498,47\t1,00
FCE 3 08\tR$ 3.356,01\t0,96
FCE 3 07\tR$ 2.908,64\t0,83
FCE 3 06\tR$ 2.463,00\t0,70
FCE 3 05\tR$ 2.099,09\t0,60
FCE 3 04\tR$ 1.553,73\t0,44
FCE 3 03\tR$ 1.294,43\t0,37
FCE 3 02\tR$ 723,98\t0,21
FCE 3 01\tR$ 428,38\t0,12
FCE 4 13\tR$ 8.651,81\t2,47
FCE 4 12\tR$ 6.513,87\t1,86
FCE 4 11\tR$ 5.193,87\t1,48
FCE 4 10\tR$ 4.455,87\t1,27
FCE 4 09\tR$ 3.498,47\t1,00
FCE 4 08\tR$ 3.356,01\t0,96
FCE 4 07\tR$ 2.908,64\t0,83
FCE 4 06\tR$ 2.463,00\t0,70
FCE 4 05\tR$ 2.099,09\t0,60
FCE 4 04\tR$ 1.553,73\t0,44
FCE 4 03\tR$ 1.294,43\t0,37
FCE 4 02\tR$ 723,98\t0,21
FCE 4 01\tR$ 428,38\t0,12"""

        df_fce_tab = pd.read_csv(io.StringIO(dados_raw_fce), sep="\t")
        st.dataframe(df_fce_tab, hide_index=True, use_container_width=True)

    with st.expander("🔄 Movimentação de servidores (Art. 38)"):
        st.markdown("""
Os servidores efetivos da carreira ATI **somente** poderão ser afastados ou cedidos nas seguintes hipóteses:

1. Requisição pela **Presidência ou Vice-Presidência da República**
2. Cessão para o **Poder Executivo Federal** — CCE ou FCE de **nível mínimo 13**
3. Cessão para **outros Poderes da União** — CCE ou FCE de **nível mínimo 15**
4. Cessão para **Secretário de Estado/DF** ou cargo equivalente ao CCE/FCE 15, ou dirigente de entidade pública em municípios com **mais de 500 mil habitantes**
        """)

    with st.expander("🏛️ Papel da Secretaria de Governo Digital (SGD)"):
        st.markdown("""
A **Secretaria de Governo Digital (SGD)** é responsável por:
- Coordenar políticas de transformação digital e interoperabilidade
- Gerir o **SISP** (Sistema de Administração dos Recursos de TI)
- **Autorizar e gerir a movimentação dos servidores ATI** entre os órgãos federais
        """)
        st.link_button("🔗 Conhecer o SISP e a SGD",
                       "https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/sisp")

    with st.expander("🤝 Associação da carreira (ANATI)"):
        st.markdown("""
A **ANATI** representa a carreira de ATI atuando em:
- Defesa institucional e acompanhamento legislativo
- Articulação com órgãos do governo
- Produção de estudos sobre governança digital
- Apoio à valorização dos profissionais de TI federal
        """)
        st.link_button("🔗 Acessar o site da ANATI", "http://anati.org.br/")

    st.divider()
    st.caption("Informações baseadas na Lei nº 14.875/2024 e nas práticas administrativas atuais da carreira ATI.")


# ================================
# RODAPÉ
# ================================
st.sidebar.divider()
st.sidebar.markdown("👨‍💻 **Feito por:** [Diego Martins](https://diegogyn.github.io/)")
st.sidebar.link_button("🐛 Dúvidas ou Sugestões", "https://github.com/diegogyn/ObservatorioATI/issues")