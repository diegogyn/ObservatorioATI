import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import re
import io
from datetime import datetime

# ================================
# Configuração da Página
# ================================
st.set_page_config(page_title="Observatório ATI", page_icon="💻", layout="wide")

# ================================
# SISTEMA DE DESIGN — TOKENS
# ================================
CORES = {
    # ── Identidade ────────────────────────────────────
    "marca":          "#0369a1",   
    "marca_escuro":   "#0c4a6e",
    "marca_fundo":    "#f0f9ff",   

    # ── Semântica positiva ────────────────────────────
    "positivo":       "#16a34a",   
    "positivo_fundo": "#f0fdf4",

    # ── Semântica negativa ────────────────────────────
    "negativo":       "#dc2626",   
    "negativo_fundo": "#fef2f2",

    # ── Semântica de atenção ──────────────────────────
    "atencao":        "#b45309",   
    "atencao_fundo":  "#fffbeb",

    # ── Texto (Otimizado para alto contraste WCAG) ────
    "texto":          "#0f172a",   
    "texto_sec":      "#334155",   
    "texto_muted":    "#475569",   

    # ── Superfícies ───────────────────────────────────
    "fundo":          "#f8fafc",
    "card":           "#ffffff",
    "borda":          "#e2e8f0",
    "borda_forte":    "#cbd5e1",

    # ── Classes da carreira ───────────────────────────
    "classe_A":       "#0369a1",   
    "classe_B":       "#7c3aed",   
    "classe_C":       "#db2777",   
    "classe_ESPECIAL":"#b45309",   

    # ── Função comissionada ───────────────────────────
    "func_sim":       "#16a34a",   
    "func_nao":       "#94a3b8",   

    # ── FCE ───────────────────────────────────────────
    "fce_base":       "#16a34a",
    "outras_func":    "#7c3aed",
    
    # ── Sidebar ───────────────────────────────────────
    "sidebar_bg":     "#e2e8f0",
    "sidebar_borda":  "#e2e8f0",
}

MAP_FUNCAO  = {"Sim": CORES["func_sim"],      "Não": CORES["func_nao"]}
MAP_CLASSES = {
    "A":       CORES["classe_A"],
    "B":       CORES["classe_B"],
    "C":       CORES["classe_C"],
    "ESPECIAL":CORES["classe_ESPECIAL"],
}

def layout_base(**extra):
    """Layout Plotly compartilhado focado em legibilidade e responsividade."""
    base = dict(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="IBM Plex Sans, sans-serif", size=13, color=CORES["texto"]),
        margin=dict(t=24, b=16, l=4, r=4),
        xaxis=dict(gridcolor="#f1f5f9", tickfont=dict(size=12, color=CORES["texto_sec"])),
        yaxis=dict(gridcolor="#f1f5f9", tickfont=dict(size=12, color=CORES["texto_sec"])),
    )
    base.update(extra)
    return base


# ================================
# CSS GLOBAL - Escopado
# ================================
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;700&display=swap');

  html, body, .stApp {{
    font-family: 'IBM Plex Sans', sans-serif;
    color: {CORES["texto"]};
  }}

  /* ── Header ─────────────────────────────────── */
  .main-header {{
    background: linear-gradient(135deg, {CORES["marca_escuro"]} 0%, #164e63 100%);
    padding: 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border-left: 6px solid {CORES["marca"]};
  }}
  .main-header h1 {{
    color: #ffffff;
    font-size: clamp(1.5rem, 4vw, 1.75rem); 
    font-weight: 700;
    margin: 0 0 0.25rem 0;
    font-family: 'IBM Plex Mono', monospace;
  }}
  .main-header p {{
    color: #bae6fd;
    margin: 0;
    font-size: 0.95rem;
    font-weight: 400;
  }}

  /* ── KPI Grid ───────────────────────────────── */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1rem;
    margin-bottom: 0.5rem;
  }}

  .kpi-card {{
    background: {CORES["card"]};
    border: 1px solid {CORES["borda"]};
    border-top: 4px solid var(--accent, {CORES["marca"]});
    border-radius: 8px;
    padding: 1.25rem 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    display: flex;
    flex-direction: column;
    justify-content: center;
  }}
  .kpi-value {{
    font-size: clamp(1.5rem, 5vw, 1.8rem);
    font-weight: 700;
    color: {CORES["texto"]};
    font-family: 'IBM Plex Mono', monospace;
    line-height: 1.2;
    word-break: break-word;
  }}
  .kpi-label {{
    font-size: 0.75rem;
    color: {CORES["texto_sec"]};
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
    margin-top: 0.4rem;
  }}
  .kpi-delta {{
    font-size: 0.8rem;
    color: {CORES["texto_muted"]};
    margin-top: 0.2rem;
    font-weight: 500;
  }}
  .kpi-delta.pos  {{ color: {CORES["positivo"]}; font-weight: 600; }}
  .kpi-delta.neg  {{ color: {CORES["negativo"]}; font-weight: 600; }}
  .kpi-delta.warn {{ color: {CORES["atencao"]};  font-weight: 600; }}

  /* ── Rótulos de gráfico ──────────────────────── */
  .sec-title {{
    font-size: 0.8rem;
    font-weight: 700;
    color: {CORES["texto_sec"]};
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid {CORES["borda"]};
    margin-bottom: 0.4rem;
  }}
  .sec-sub {{
    font-size: 0.85rem;
    color: {CORES["texto_muted"]};
    margin-bottom: 1rem;
    line-height: 1.4;
  }}

  /* ── Caixas contextuais ──────────────────────── */
  .box-info {{
    background: {CORES["marca_fundo"]};
    border: 1px solid #bae6fd;
    border-left: 4px solid {CORES["marca"]};
    border-radius: 8px;
    padding: 1rem;
    font-size: 0.9rem;
    color: {CORES["marca_escuro"]};
    margin-bottom: 1.5rem;
    line-height: 1.6;
  }}
  .box-alerta {{
    background: {CORES["negativo_fundo"]};
    border: 1px solid #fca5a5;
    border-left: 4px solid {CORES["negativo"]};
    border-radius: 8px;
    padding: 1rem;
    font-size: 0.9rem;
    color: #7f1d1d;
    margin-top: 1rem;
    line-height: 1.6;
  }}

  /* ── Badge de data ───────────────────────────── */
  .ref-badge {{
    display: inline-block;
    background: #1e3a5f;
    color: #bae6fd;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.3rem 0.75rem;
    border-radius: 20px;
    margin-bottom: 1rem;
    letter-spacing: 0.03em;
  }}

  /* ── Divisor ─────────────────────────────────── */
  .div-sec {{
    height: 1px;
    background: {CORES["borda"]};
    margin: 2rem 0;
  }}
  
  /* ── Sidebar ─────────────────────────────────── */
  section[data-testid="stSidebar"] {{
    background: {CORES["sidebar_bg"]};
  }}
  
  /* Títulos (ex: 💻 Observatório ATI) e markdown geral */
  section[data-testid="stSidebar"] h1,
  section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3,
  section[data-testid="stSidebar"] .stMarkdown p {{
    color: #ffffff !important;
  }}

  /* Rótulos dos Filtros (ex: Órgão de Exercício) */
  section[data-testid="stSidebar"] label p {{
    color: #94a3b8 !important;
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
  }}

  /* Textos das opções nos Radios (Todos, Sim, Não, Sobre a Carreira, etc) */
  section[data-testid="stSidebar"] div[role="radiogroup"] p {{
    color: #ffffff !important; 
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    text-transform: none;
  }}

  /* Selectbox - Texto escuro para contrastar com o input nativo claro */
  section[data-testid="stSidebar"] div[data-baseweb="select"] {{
    color: #0f172a !important;
  }}

  /* Botão de Link (Dúvidas, Sugestões) e Botões nativos */
  section[data-testid="stSidebar"] .stLinkButton a,
  section[data-testid="stSidebar"] .stLinkButton p {{
    color: #0f172a !important; /* Escuro, pois o fundo do botão é branco/claro */
    font-weight: 600 !important;
  }}

  section[data-testid="stSidebar"] hr {{
    border-color: {CORES["sidebar_borda"]} !important;
  }}
</style>
""", unsafe_allow_html=True)


# ================================
# CARREGAMENTO DE DADOS
# ================================
@st.cache_data
def load_data():
    caminho_arquivo      = os.path.join("data", "dados_atis.csv")
    caminho_meta         = os.path.join("data", "metadata.json")
    caminho_desligamentos= os.path.join("data", "desligamentos-ati-pep-fev-2026.csv")

    data_ref = "Atualização Pendente"
    if os.path.exists(caminho_meta):
        with open(caminho_meta, "r", encoding="utf-8") as f:
            data_ref = json.load(f).get("data_referencia", "Desconhecida")

    try:
        df = pd.read_csv(caminho_arquivo)
    except FileNotFoundError:
        df = pd.DataFrame()

    if not df.empty:
        df["Classe"] = df["Nível/Padrão"].apply(
            lambda x: str(x).split("-")[0].strip().upper() if pd.notna(x) else "Desconhecida"
        )
        df["Ano de Ingresso"] = df["Ingresso Serviço Público"].apply(
            lambda x: str(x)[-4:] if "/" in str(x) else "Desconhecido"
        )
        df["Ingresso Serviço Público (dt)"] = pd.to_datetime(
            df["Ingresso Serviço Público"], format="%d/%m/%Y", errors="coerce"
        )

        def classificar_funcao(funcao):
            funcao = str(funcao).strip().upper()
            if funcao in ["SEM FUNÇÃO", "NAN", ""]:
                return "Sem Função", "Sem Função", "Sem Função", -1
            match = re.search(r'\b(FCE)\b.*?(?:[^\d]|^)(\d{2})\b', funcao)
            if match:
                nivel = match.group(2)
                if nivel.isdigit() and 1 <= int(nivel) <= 17:
                    return f"FCE Nível {nivel}", "FCE", f"Nível {nivel}", int(nivel)
            return "Outras Funções", "Outras Funções", "Outras", 0

        if "Função" in df.columns:
            res = df["Função"].apply(classificar_funcao)
            df["Função Resumo"] = [r[0] for r in res]
            df["Tipo Função"]   = [r[1] for r in res]
            df["Nível Função"]  = [r[2] for r in res]
            df["Ordem Nível"]   = [r[3] for r in res]
        else:
            df["Função Resumo"] = df["Tipo Função"] = df["Nível Função"] = "Desconhecida"
            df["Ordem Nível"] = -1

    try:
        df_deslig = pd.read_csv(caminho_desligamentos, encoding="utf-8-sig")
        df_deslig = df_deslig[df_deslig["Ano"].astype(str).str.isnumeric()]
        df_deslig = df_deslig.rename(columns={"Quantidade de Desligamentos": "Desligamentos"})
        df_deslig["Ano"]          = df_deslig["Ano"].astype(str)
        df_deslig["Desligamentos"]= df_deslig["Desligamentos"].astype(int)
        df_deslig = df_deslig[["Ano", "Desligamentos"]]
    except FileNotFoundError:
        df_deslig = pd.DataFrame(columns=["Ano", "Desligamentos"])

    return df, data_ref, df_deslig


df, data_ref, df_deslig = load_data()

# ================================
# SIDEBAR
# ================================
with st.sidebar:
    st.markdown("### 💻 Observatório ATI")
    st.markdown(f'<div class="ref-badge">📅 {data_ref}</div>', unsafe_allow_html=True)

    pagina = st.radio(
        "Página", ["📊 Observatório ATI", "📚 Sobre a Carreira"],
        label_visibility="collapsed"
    )
    st.divider()


# ══════════════════════════════════════════════════════════
# PÁGINA 1 — OBSERVATÓRIO
# ══════════════════════════════════════════════════════════
if pagina == "📊 Observatório ATI":

    st.markdown("""
    <div class="main-header">
        <h1>// Observatório ATI</h1>
        <p>Painel analítico · Analistas em Tecnologia da Informação · Executivo Federal</p>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.warning("⚠️ Dados não encontrados. Execute o pipeline de extração primeiro.")
        st.stop()

    # Filtros ─────────────────────────────────────────────
    with st.sidebar:
        st.markdown("**🔍 Filtros**")
        orgaos = ["Todos"] + sorted(df["Órgão de Exercício"].dropna().unique())
        orgao_sel = st.selectbox("Órgão de Exercício", orgaos)

        func_sel = st.radio("Ocupa Função Comissionada?", ["Todos", "Sim", "Não"])

        classes = ["Todas"] + sorted(df[df["Classe"] != "Desconhecida"]["Classe"].unique())
        classe_sel = st.selectbox("Classe na Carreira", classes)

        anos_v = sorted([a for a in df["Ano de Ingresso"].unique() if a.isdigit()], reverse=True)
        ano_sel = st.selectbox("Ano de Ingresso (SP)", ["Todos"] + anos_v)

    # Aplicação dos filtros ───────────────────────────────
    df_f = df.copy()
    if orgao_sel  != "Todos":  df_f = df_f[df_f["Órgão de Exercício"] == orgao_sel]
    if func_sel   != "Todos":  df_f = df_f[df_f["Tem Função?"]        == func_sel]
    if classe_sel != "Todas":  df_f = df_f[df_f["Classe"]             == classe_sel]
    if ano_sel    != "Todos":  df_f = df_f[df_f["Ano de Ingresso"]    == ano_sel]

    # Cálculos KPI ────────────────────────────────────────
    total     = len(df_f)
    n_func    = (df_f["Tem Função?"] == "Sim").sum()
    perc_func = (n_func / total * 100) if total > 0 else 0
    n_orgaos  = df_f["Órgão de Exercício"].nunique()
    ano_moda  = df_f["Ano de Ingresso"].mode()[0] if not df_f.empty else "—"

    hoje = datetime.today()
    df_cd = df_f.dropna(subset=["Ingresso Serviço Público (dt)"])
    media_anos_str = (
        f"{((hoje - df_cd['Ingresso Serviço Público (dt)']).dt.days / 365.25).mean():.1f} anos"
        if not df_cd.empty else "—"
    )

    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card" style="--accent:{CORES['marca']}">
        <div class="kpi-value">{total:,}</div>
        <div class="kpi-label">Total de ATIs</div>
        <div class="kpi-delta">Base: {data_ref}</div>
      </div>
      <div class="kpi-card" style="--accent:{CORES['func_sim']}">
        <div class="kpi-value">{n_func:,}</div>
        <div class="kpi-label">Com Função</div>
        <div class="kpi-delta pos">{perc_func:.1f}% do total filtrado</div>
      </div>
      <div class="kpi-card" style="--accent:{CORES['marca']}">
        <div class="kpi-value">{n_orgaos}</div>
        <div class="kpi-label">Órgãos Distintos</div>
        <div class="kpi-delta">No filtro atual</div>
      </div>
      <div class="kpi-card" style="--accent:{CORES['atencao']}">
        <div class="kpi-value">{ano_moda}</div>
        <div class="kpi-label">Ano de Ingresso</div>
        <div class="kpi-delta">Mais frequente (moda)</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="div-sec"></div>', unsafe_allow_html=True)

    # ════════════════════════════════
    # BLOCO 1 — DISTRIBUIÇÃO ESTRUTURAL
    # ════════════════════════════════
    st.markdown("### 🏛️ Distribuição Estrutural")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="sec-title">Top 10 Órgãos com mais ATIs</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-sub">Empilhado por ocupação de função comissionada</div>', unsafe_allow_html=True)

        top10 = df_f["Órgão de Exercício"].value_counts().head(10).index.tolist()
        df_of = (df_f[df_f["Órgão de Exercício"].isin(top10)]
                 .groupby(["Órgão de Exercício", "Tem Função?"])
                 .size().reset_index(name="Qtd"))

        fig = px.bar(df_of, x="Qtd", y="Órgão de Exercício",
                     color="Tem Função?", orientation="h",
                     color_discrete_map=MAP_FUNCAO,
                     category_orders={"Órgão de Exercício": top10[::-1]})
        fig.update_layout(**layout_base(
            barmode="stack",
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, font=dict(size=12)),
            yaxis=dict(tickfont=dict(size=11, color=CORES["texto_sec"]))
        ))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="sec-title">Distribuição por Nível/Padrão</div>', unsafe_allow_html=True)
        modo_pct = st.toggle("Ver em Percentual (%)", value=False, key="t_niveis")
        st.markdown('<div class="sec-sub">Posição de cada servidor na carreira</div>', unsafe_allow_html=True)

        df_niv = (df_f.groupby(["Nível/Padrão", "Tem Função?"])
                  .size().reset_index(name="Qtd")
                  .sort_values("Nível/Padrão"))

        fig2 = px.bar(df_niv, x="Nível/Padrão", y="Qtd", color="Tem Função?",
                      color_discrete_map=MAP_FUNCAO,
                      barmode="relative" if modo_pct else "stack")
        fig2.update_layout(**layout_base(
            barnorm="percent" if modo_pct else None,
            yaxis_title="% de Servidores" if modo_pct else "Quantidade",
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, font=dict(size=12)),
            xaxis=dict(tickangle=-45, tickfont=dict(size=11))
        ))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="div-sec"></div>', unsafe_allow_html=True)

    # ════════════════════════════════
    # BLOCO 2 — SENIORIDADE E INGRESSO
    # ════════════════════════════════
    st.markdown("### ⏳ Senioridade e Perfil de Ingresso")
    col3, col4, col5 = st.columns([2, 1.4, 1.6])

    with col3:
        st.markdown('<div class="sec-title">Histórico de Ingresso no Serviço Público</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-sub">Número de ATIs que ingressaram a cada ano</div>', unsafe_allow_html=True)

        df_ing = (df_f[df_f["Ano de Ingresso"] != "Desconhecido"]
                  .groupby("Ano de Ingresso").size()
                  .reset_index(name="Quantidade")
                  .sort_values("Ano de Ingresso"))

        if not df_ing.empty:
            fig3 = px.area(df_ing, x="Ano de Ingresso", y="Quantidade",
                           markers=True, text="Quantidade",
                           color_discrete_sequence=[CORES["marca"]])
            fig3.update_traces(
                textposition="top center",
                textfont=dict(size=11, color=CORES["texto_sec"]),
                line=dict(width=2.5),
                fillcolor="rgba(3,105,161,0.10)"
            )
            fig3.update_layout(**layout_base(
                yaxis_title="Qtd de Ingressos", xaxis_title="Ano",
                xaxis=dict(tickangle=-45, tickfont=dict(size=11))
            ))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sem dados de ingresso no filtro atual.")

    with col4:
        st.markdown('<div class="sec-title">Distribuição por Classe</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-sub">Senioridade macro (A → Especial)</div>', unsafe_allow_html=True)

        df_cl  = df_f[df_f["Classe"] != "Desconhecida"]
        ordem4 = ["A", "B", "C", "ESPECIAL"]
        if not df_cl.empty:
            df_cnt = df_cl.groupby("Classe").size().reset_index(name="Quantidade")
            df_cnt["Classe"] = pd.Categorical(df_cnt["Classe"], categories=ordem4, ordered=True)
            df_cnt = df_cnt.sort_values("Classe")

            fig4 = px.pie(df_cnt, values="Quantidade", names="Classe",
                          hole=0.45, color="Classe", color_discrete_map=MAP_CLASSES)
            fig4.update_traces(
                textinfo="percent+label",
                textposition="inside",
                textfont=dict(size=12, color="#ffffff")
            )
            fig4.update_layout(
                showlegend=False,
                margin=dict(t=8, b=8, l=0, r=0),
                paper_bgcolor="white",
                font=dict(family="IBM Plex Sans", size=13)
            )
            st.plotly_chart(fig4, use_container_width=True)

    with col5:
        st.markdown('<div class="sec-title">Classe × Função</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-sub">Concentração de FCE por classe da carreira</div>', unsafe_allow_html=True)

        df_ht = df_f[df_f["Classe"] != "Desconhecida"]
        if not df_ht.empty:
            df_hp = df_ht.groupby(["Classe", "Tem Função?"]).size().reset_index(name="Qtd")
            df_hp["Classe"] = pd.Categorical(df_hp["Classe"], categories=ordem4, ordered=True)
            df_hp = df_hp.sort_values("Classe")

            fig5 = px.density_heatmap(df_hp, x="Classe", y="Tem Função?", z="Qtd",
                                      color_continuous_scale=[
                                          [0.0, "#f0f9ff"],
                                          [0.5, "#0369a1"],
                                          [1.0, "#0c4a6e"]
                                      ],
                                      text_auto=True)
            fig5.update_traces(textfont=dict(size=14, color="#ffffff"))
            fig5.update_layout(**layout_base(
                coloraxis_showscale=False,
                xaxis_title="Classe",
                yaxis_title="Tem Função?"
            ))
            st.plotly_chart(fig5, use_container_width=True)

    st.markdown('<div class="div-sec"></div>', unsafe_allow_html=True)

    # ════════════════════════════════
    # BLOCO 3 — CONCENTRAÇÃO POR ÓRGÃO
    # ════════════════════════════════
    st.markdown("### 🗺️ Concentração por Órgão")
    col6, col7 = st.columns([1.5, 2])

    with col6:
        st.markdown('<div class="sec-title">Peso Relativo por Órgão (Treemap)</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-sub">Proporção visual — top 20 órgãos</div>', unsafe_allow_html=True)

        df_tm = (df_f.groupby("Órgão de Exercício").size()
                 .reset_index(name="Quantidade")
                 .sort_values("Quantidade", ascending=False)
                 .head(20))

        fig6 = px.treemap(df_tm, path=["Órgão de Exercício"], values="Quantidade",
                          color="Quantidade",
                          # Troquei o #dbeafe inicial por #38bdf8
                          color_continuous_scale=[[0, "#38bdf8"], [0.5, "#0369a1"], [1, "#0c4a6e"]])
        fig6.update_traces(
            textinfo="label+value",
            textfont=dict(size=12, color="#ffffff"), # Mantemos o texto branco
            marker=dict(cornerradius=4)
        )
        fig6.update_layout(
            margin=dict(t=8, b=8, l=0, r=0),
            coloraxis_showscale=False,
            paper_bgcolor="white",
            font=dict(family="IBM Plex Sans", size=13)
        )
        st.plotly_chart(fig6, use_container_width=True)

    with col7:
        st.markdown('<div class="sec-title">Taxa de Ocupação de Função por Órgão</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-sub">Top 15 por % de ATIs com função comissionada (mín. 3 ATIs)</div>', unsafe_allow_html=True)

        df_tx = (df_f.groupby("Órgão de Exercício")
                 .apply(lambda g: pd.Series({
                     "Total": len(g),
                     "Com Função": (g["Tem Função?"] == "Sim").sum()
                 }))
                 .reset_index())
        df_tx["Taxa (%)"] = (df_tx["Com Função"] / df_tx["Total"] * 100).round(1)
        df_tx = (df_tx[df_tx["Total"] >= 3]
                 .sort_values("Taxa (%)", ascending=False).head(15))

        fig7 = px.bar(df_tx, x="Taxa (%)", y="Órgão de Exercício",
                      orientation="h", text="Taxa (%)",
                      color="Taxa (%)",
                      color_continuous_scale=[[0, "#dbeafe"], [0.6, "#0369a1"], [1, "#16a34a"]])
        fig7.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside",
            textfont=dict(size=12, color=CORES["texto_sec"])
        )
        fig7.update_layout(**layout_base(
            coloraxis_showscale=False,
            xaxis=dict(range=[0, df_tx["Taxa (%)"].max() * 1.15 if not df_tx.empty else 100],
                       ticksuffix="%"),
            yaxis=dict(categoryorder="total ascending", tickfont=dict(size=11))
        ))
        st.plotly_chart(fig7, use_container_width=True)

    st.markdown('<div class="div-sec"></div>', unsafe_allow_html=True)

    # ════════════════════════════════
    # BLOCO 4 — RAIO-X FCE
    # ════════════════════════════════
    st.markdown("### 🎯 Raio-X das Funções Comissionadas Executivas (FCE)")
    st.markdown("""
    <div class="box-info">
      💡 <strong>Como ler:</strong> As funções FCE são agrupadas pelos dois últimos dígitos
      (ex: 05, 10, 13), que indicam o nível hierárquico da função. Funções de outro tipo são
      agrupadas em "Outras Funções".
    </div>
    """, unsafe_allow_html=True)

    col_f1, col_f2, col_f3 = st.columns([1, 2, 1.5])

    with col_f1:
        st.markdown('<div class="sec-title">Proporção de Vínculos</div>', unsafe_allow_html=True)

        df_pz = (df_f[df_f["Tipo Função"] != "Sem Função"]["Tipo Função"]
                 .value_counts().reset_index())
        df_pz.columns = ["Tipo", "Quantidade"]

        if not df_pz.empty:
            fig10 = px.pie(df_pz, values="Quantidade", names="Tipo", hole=0.5,
                           color="Tipo",
                           color_discrete_map={
                               "FCE":           CORES["fce_base"],
                               "Outras Funções":CORES["outras_func"]
                           })
            fig10.update_traces(
                textposition="inside",
                textinfo="percent+label",
                textfont=dict(size=12, color="#ffffff")
            )
            fig10.update_layout(
                showlegend=False,
                margin=dict(t=8, b=8, l=0, r=0),
                paper_bgcolor="white",
                font=dict(family="IBM Plex Sans", size=13)
            )
            st.plotly_chart(fig10, use_container_width=True)
        else:
            st.warning("Sem dados de função para exibir.")

    with col_f2:
        st.markdown('<div class="sec-title">Distribuição por Nível FCE (01 → 17)</div>', unsafe_allow_html=True)

        df_fce = df_f[df_f["Tipo Função"] == "FCE"]
        if not df_fce.empty:
            df_bn = (df_fce.groupby(["Nível Função", "Ordem Nível"])
                     .size().reset_index(name="Quantidade")
                     .sort_values("Ordem Nível"))

            fig11 = px.bar(df_bn, x="Nível Função", y="Quantidade",
                           text="Quantidade",
                           color="Ordem Nível",
                           color_continuous_scale=[
                               [0.0, "#dcfce7"],   
                               [0.5, "#16a34a"],   
                               [1.0, "#14532d"]    
                           ])
            fig11.update_traces(
                textposition="outside",
                textfont=dict(size=11, color=CORES["texto_sec"])
            )
            fig11.update_layout(**layout_base(
                coloraxis_showscale=False,
                xaxis_title="Nível FCE",
                yaxis_title="Quantidade de Servidores"
            ))
            st.plotly_chart(fig11, use_container_width=True)
        else:
            st.info("Nenhum servidor FCE no filtro atual.")

    with col_f3:
        st.markdown('<div class="sec-title">Nível Médio FCE por Classe</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-sub">Classes mais seniores ocupam posições mais altas?</div>', unsafe_allow_html=True)

        df_fc = df_f[df_f["Tipo Função"] == "FCE"].copy()
        df_fc = df_fc[df_fc["Classe"] != "Desconhecida"]

        if not df_fc.empty:
            df_md = (df_fc.groupby("Classe")["Ordem Nível"]
                     .agg(["mean", "count"])
                     .reset_index())
            df_md.columns = ["Classe", "Nível Médio FCE", "Qtd"]
            df_md["Nível Médio FCE"] = df_md["Nível Médio FCE"].round(1)
            df_md = df_md.sort_values("Nível Médio FCE", ascending=False)

            fig12 = px.bar(df_md, x="Classe", y="Nível Médio FCE",
                           text="Nível Médio FCE",
                           color="Classe",
                           color_discrete_map=MAP_CLASSES)
            fig12.update_traces(
                textposition="outside",
                textfont=dict(size=12, color=CORES["texto_sec"])
            )
            fig12.update_layout(**layout_base(
                showlegend=False,
                yaxis=dict(range=[0, 18], gridcolor="#f1f5f9"),
                xaxis_title="Classe",
                yaxis_title="Nível Médio FCE"
            ))
            st.plotly_chart(fig12, use_container_width=True)
        else:
            st.info("Sem dados FCE no filtro atual.")

    st.markdown('<div class="div-sec"></div>', unsafe_allow_html=True)

    # ════════════════════════════════════
    # BLOCO 5 — BALANÇO INGRESSOS × EVASÃO
    # ════════════════════════════════════
    st.markdown("### ⚖️ Balanço da Carreira — Ingressos vs. Evasão")
    st.markdown(
        "_Visão global da carreira. Não altera com os filtros laterais, pois os dados de "
        "desligamento não possuem detalhamento por órgão/classe._"
    )

    if not df_deslig.empty:
        df_ig = (df[df["Ano de Ingresso"] != "Desconhecido"]
                 .groupby("Ano de Ingresso").size()
                 .reset_index(name="Ingressos")
                 .rename(columns={"Ano de Ingresso": "Ano"}))

        df_bal = pd.merge(df_ig, df_deslig, on="Ano", how="outer").fillna(0)
        df_bal["Ingressos"]      = df_bal["Ingressos"].astype(int)
        df_bal["Desligamentos"]  = df_bal["Desligamentos"].astype(int)
        df_bal = df_bal[df_bal["Ano"].astype(int) >= 2010].sort_values("Ano")
        df_bal["Saldo"] = df_bal["Ingressos"] - df_bal["Desligamentos"]

        tot_ing = df_bal["Ingressos"].sum()
        tot_des = df_bal["Desligamentos"].sum()
        saldo   = tot_ing - tot_des
        tx_ev   = (tot_des / tot_ing * 100) if tot_ing > 0 else 0

        b1, b2, b3, b4 = st.columns(4)
        dados_kpi_b = [
            (b1, f"{tot_ing:,}",  "Ingressos (desde 2010)",     CORES["marca"],    ""),
            (b2, f"{tot_des:,}",  "Desligamentos (desde 2010)", CORES["negativo"], "neg"),
            (b3, (f"+{saldo:,}" if saldo >= 0 else f"{saldo:,}"),
                 "Saldo Líquido",
                 CORES["positivo"] if saldo >= 0 else CORES["negativo"],
                 "pos" if saldo >= 0 else "neg"),
            (b4, f"{tx_ev:.1f}%","Taxa de Evasão",              CORES["atencao"],  "warn"),
        ]
        for col, val, lbl, accent, delta_cls in dados_kpi_b:
            with col:
                st.markdown(f"""
                <div class="kpi-card" style="--accent:{accent}">
                  <div class="kpi-value">{val}</div>
                  <div class="kpi-label">{lbl}</div>
                  <div class="kpi-delta {delta_cls}">Período 2010–atual</div>
                </div>
                """, unsafe_allow_html=True)

        st.write("")
        col_b1, col_b2 = st.columns([3, 1])

        with col_b1:
            st.markdown('<div class="sec-title">Ingressos vs. Desligamentos por Ano</div>', unsafe_allow_html=True)

            df_melt = df_bal.melt(id_vars="Ano",
                                  value_vars=["Ingressos", "Desligamentos"],
                                  var_name="Movimentação", value_name="Quantidade")
            fig8 = px.bar(df_melt, x="Ano", y="Quantidade",
                          color="Movimentação", barmode="group",
                          color_discrete_map={
                              "Ingressos":      CORES["positivo"],
                              "Desligamentos":  CORES["negativo"]
                          },
                          text_auto=True)
            fig8.update_traces(
                textposition="outside",
                textfont=dict(size=11, color=CORES["texto_sec"])
            )
            fig8.update_layout(**layout_base(
                yaxis_title="Qtd. de Servidores", xaxis_title="",
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1, font=dict(size=12))
            ))
            st.plotly_chart(fig8, use_container_width=True)

        with col_b2:
            st.markdown('<div class="sec-title">Saldo Líquido Anual</div>', unsafe_allow_html=True)
            st.markdown('<div class="sec-sub">Verde = ganho · Vermelho = perda</div>', unsafe_allow_html=True)

            cores_saldo = [CORES["positivo"] if s >= 0 else CORES["negativo"]
                           for s in df_bal["Saldo"]]
            fig9 = go.Figure(go.Bar(
                x=df_bal["Saldo"], y=df_bal["Ano"],
                orientation="h",
                marker_color=cores_saldo,
                text=df_bal["Saldo"],
                textposition="outside",
                textfont=dict(size=11, color=CORES["texto_sec"])
            ))
            fig9.add_vline(x=0, line_width=1.5, line_color=CORES["borda_forte"])
            fig9.update_layout(**layout_base(
                yaxis=dict(tickfont=dict(size=10)),
                showlegend=False
            ))
            st.plotly_chart(fig9, use_container_width=True)

        st.markdown("""
        <div class="box-alerta">
          <strong>⚠️ Atenção:</strong> Os dados consideram apenas ATIs que assumiram e depois
          saíram. A evasão real é ainda maior ao incluir aprovados que não tomaram posse.
          Isso compromete a <strong>Estratégia de Governo Digital</strong>: maior terceirização,
          perda de conhecimento institucional, atraso em projetos estratégicos e exposição a
          riscos de segurança da informação.
        </div>
        """, unsafe_allow_html=True)

    else:
        st.info("Nenhum dado de evasão encontrado. Adicione `desligamentos-ati-pep-fev-2026.csv` na pasta `data`.")

    st.markdown('<div class="div-sec"></div>', unsafe_allow_html=True)


    # ════════════════════════════════
    # TABELA FINAL
    # ════════════════════════════════
    st.markdown("### 📋 Base de Dados Completa")

    cs, cd = st.columns([3, 1])
    with cs:
        busca = st.text_input("🔍 Buscar por nome ou órgão:",
                              placeholder="Digite para filtrar a tabela…")
    with cd:
        st.write("")
        csv_exp = df_f.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Exportar CSV", data=csv_exp,
            file_name=f"atis_{data_ref.replace(' ', '_')}.csv",
            mime="text/csv", use_container_width=True
        )

    df_exib = df_f.drop(
        columns=["Classe", "Ano de Ingresso", "Ordem Nível", "Tipo Função",
                 "Nível Função", "Ingresso Serviço Público (dt)"],
        errors="ignore"
    )
    if busca:
        mask = df_exib.apply(
            lambda c: c.astype(str).str.contains(busca, case=False, na=False)
        ).any(axis=1)
        df_exib = df_exib[mask]

    st.dataframe(df_exib, use_container_width=True, hide_index=True)
    st.caption(f"Exibindo {len(df_exib):,} de {total:,} registros no filtro.")


# ══════════════════════════════════════════════════════════
# PÁGINA 2 — SOBRE A CARREIRA
# ══════════════════════════════════════════════════════════
elif pagina == "📚 Sobre a Carreira":

    st.markdown("""
    <div class="main-header">
        <h1>// Carreira ATI</h1>
        <p>Lei nº 14.875, de 31 de maio de 2024 · Guia da carreira de Analista em Tecnologia da Informação</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🖥️ O que faz o ATI?", expanded=True):
        st.write("""
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
        st.write("""
A remuneração é estruturada no modelo de **subsídio** — parcela única mensal, sem gratificações incorporadas.

Verbas indenizatórias adicionais:
- Auxílio-alimentação
- Auxílio-transporte 
- Auxílio-saúde
- Auxílio pré-escolar
- 13º salário
-1/3 constitucional de férias
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
        st.write("""
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
        st.write("""
Os servidores efetivos da carreira ATI **somente** poderão ser afastados ou cedidos nas seguintes hipóteses:

1. Requisição pela **Presidência ou Vice-Presidência da República**
2. Cessão para o **Poder Executivo Federal** — CCE ou FCE de **nível mínimo 13**
3. Cessão para **outros Poderes da União** — CCE ou FCE de **nível mínimo 15**
4. Cessão para **Secretário de Estado/DF** ou cargo equivalente ao CCE/FCE 15, ou dirigente de entidade pública em municípios com **mais de 500 mil habitantes**
        """)

    with st.expander("🏛️ Papel da Secretaria de Governo Digital (SGD)"):
        st.write("""
A **Secretaria de Governo Digital (SGD)** é responsável por:
- Coordenar políticas de transformação digital e interoperabilidade
- Gerir o **SISP** (Sistema de Administração dos Recursos de TI)
- **Autorizar e gerir a movimentação dos servidores ATI** entre os órgãos federais
        """)
        st.link_button("🔗 Conhecer o SISP e a SGD",
                       "https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/sisp")

    with st.expander("🤝 Associação da carreira (ANATI)"):
        st.write("""
A **ANATI** representa a carreira de ATI atuando em:
- Defesa institucional e acompanhamento legislativo
- Articulação com órgãos do governo
- Produção de estudos sobre governança digital
- Apoio à valorização dos profissionais de TI federal
        """)
        st.link_button("🔗 Acessar o site da ANATI", "http://anati.org.br/")

    st.divider()
    st.caption("Informações baseadas na Lei nº 14.875/2024 e nas práticas administrativas atuais da carreira ATI.")

# ══════════════════════════════════════════════════════════
# RODAPÉ LATERAL
# ══════════════════════════════════════════════════════════
st.sidebar.divider()
st.sidebar.markdown("👨‍💻 **Feito por:** [Diego Martins](https://diegogyn.github.io/)")
st.sidebar.link_button("🐛 Dúvidas, Sugestões ou Erros",
                       "https://github.com/diegogyn/ObservatorioATI/issues")