import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json

st.set_page_config(page_title="Observatório ATI", page_icon="💻", layout="wide")

@st.cache_data
def load_data():
    caminho_arquivo = os.path.join('data', 'dados_atis.csv')
    caminho_meta = os.path.join('data', 'metadata.json')
    
    # Tenta ler a data de referência
    data_ref = "Atualização Pendente"
    if os.path.exists(caminho_meta):
        with open(caminho_meta, "r", encoding="utf-8") as f:
            data_ref = json.load(f).get("data_referencia", "Desconhecida")
            
    try:
        df = pd.read_csv(caminho_arquivo)
    except FileNotFoundError:
        df = pd.DataFrame()
        
    # Extrai a Classe (S, A, B, C) e o Ano de Ingresso para os novos filtros
    if not df.empty:
        df['Classe'] = df['Nível/Padrão'].apply(lambda x: str(x).split('/')[0].strip() if pd.notna(x) else 'Desconhecida')
        df['Ano de Ingresso'] = df['Ingresso Serviço Público'].apply(lambda x: str(x)[-4:] if '/' in str(x) else 'Desconhecido')
        
    return df, data_ref

df, data_ref = load_data()

# Cabeçalho
st.title("💻 Observatório da Carreira ATI")
st.markdown("Painel interativo com a distribuição dos **Analistas em Tecnologia da Informação** do Executivo Federal.")
st.divider()

if df.empty:
    st.warning("⚠️ Dados não encontrados. Execute o pipeline de extração primeiro.")
    st.stop()

# ================================
# BARRA LATERAL (MENU DE FILTROS)
# ================================
st.sidebar.markdown(f"**📅 Mês de Referência:**\n\n*{data_ref}*")
st.sidebar.divider()

st.sidebar.header("🔍 Filtros do Painel")

# Filtro 1: Órgão
orgaos = ["Todos"] + sorted(list(df['Órgão de Exercício'].dropna().unique()))
orgao_selecionado = st.sidebar.selectbox("Órgão de Exercício:", orgaos)

# Filtro 2: Função Comissionada
tem_funcao_opcoes = ["Todos", "Sim", "Não"]
funcao_selecionada = st.sidebar.radio("Ocupa Função Comissionada?", tem_funcao_opcoes)

# Filtro 3: Classe da Carreira (NOVO)
classes =["Todas"] + sorted(list(df[df['Classe'] != 'Desconhecida']['Classe'].unique()))
classe_selecionada = st.sidebar.selectbox("Classe na Carreira:", classes)

# Filtro 4: Ano de Ingresso (NOVO)
anos_validos = sorted([ano for ano in df['Ano de Ingresso'].unique() if ano.isdigit()], reverse=True)
anos = ["Todos"] + anos_validos
ano_selecionado = st.sidebar.selectbox("Ano de Ingresso (Serviço Público):", anos)

# Aplicando os filtros no DataFrame
df_filtrado = df.copy()
if orgao_selecionado != "Todos": df_filtrado = df_filtrado[df_filtrado['Órgão de Exercício'] == orgao_selecionado]
if funcao_selecionada != "Todos": df_filtrado = df_filtrado[df_filtrado['Tem Função?'] == funcao_selecionada]
if classe_selecionada != "Todas": df_filtrado = df_filtrado[df_filtrado['Classe'] == classe_selecionada]
if ano_selecionado != "Todos": df_filtrado = df_filtrado[df_filtrado['Ano de Ingresso'] == ano_selecionado]

# ================================
# KPIs e GRÁFICOS
# ================================
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Total de ATIs (Filtro)", len(df_filtrado))
with col2: 
    atis_func = len(df_filtrado[df_filtrado['Tem Função?'] == 'Sim'])
    perc = (atis_func / len(df_filtrado) * 100) if len(df_filtrado) > 0 else 0
    st.metric("Com Função", f"{atis_func} ({perc:.1f}%)")
with col3: st.metric("Órgãos Distintos", df_filtrado['Órgão de Exercício'].nunique())
with col4: 
    ano_mais_comum = df_filtrado['Ano de Ingresso'].mode()[0] if not df_filtrado.empty else "-"
    st.metric("Ano de Ingresso (Moda)", ano_mais_comum)

st.divider()

colA, colB = st.columns(2)
with colA:
    st.subheader("🏢 Top 10 Órgãos com mais ATIs")
    df_orgaos = df_filtrado['Órgão de Exercício'].value_counts().reset_index().head(10)
    df_orgaos.columns =['Órgão', 'Quantidade']
    fig_orgaos = px.bar(df_orgaos, x='Quantidade', y='Órgão', orientation='h', color='Quantidade', color_continuous_scale='Blues')
    fig_orgaos.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_orgaos, use_container_width=True)

with colB:
    st.subheader("📊 Distribuição por Nível da Carreira")
    df_niveis = df_filtrado.groupby(['Nível/Padrão', 'Tem Função?']).size().reset_index(name='Quantidade')
    df_niveis = df_niveis.sort_values(by='Nível/Padrão')
    fig_niveis = px.bar(df_niveis, x='Nível/Padrão', y='Quantidade', color='Tem Função?', barmode='stack', color_discrete_map={'Sim': '#1f77b4', 'Não': '#ff7f0e'})
    st.plotly_chart(fig_niveis, use_container_width=True)

st.subheader("📋 Tabela Analítica Detalhada")
# Remove colunas auxiliares antes de exibir
df_exibicao = df_filtrado.drop(columns=['Classe', 'Ano de Ingresso'])
st.dataframe(df_exibicao, use_container_width=True, hide_index=True)