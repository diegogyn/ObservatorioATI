import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json

# ================================
# Configuração da Página
# ================================
st.set_page_config(page_title="Observatório ATI", page_icon="💻", layout="wide")

# ================================
# FUNÇÃO DE CARREGAMENTO DE DADOS
# ================================
@st.cache_data
def load_data():

    caminho_arquivo = os.path.join("data", "dados_atis.csv")
    caminho_meta = os.path.join("data", "metadata.json")

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
            lambda x: str(x).split("/")[0].strip() if pd.notna(x) else "Desconhecida"
        )

        df["Ano de Ingresso"] = df["Ingresso Serviço Público"].apply(
            lambda x: str(x)[-4:] if "/" in str(x) else "Desconhecido"
        )

    return df, data_ref


df, data_ref = load_data()

# ================================
# MENU LATERAL
# ================================
#st.sidebar.image(
#    "https://img.icons8.com/color/96/000000/brazil.png",
#    width=60
#)

pagina = st.sidebar.radio(
    "📌 Navegação do Painel",
    ["📊 Observatório ATI", "📚 Sobre a Carreira"]
)

st.sidebar.divider()

# ================================
# PÁGINA 1 - OBSERVATÓRIO
# ================================
if pagina == "📊 Observatório ATI":

    st.title("💻 Observatório da Carreira ATI")

    st.markdown(
        "Painel interativo com a distribuição dos **Analistas em Tecnologia da Informação** do Executivo Federal."
    )

    st.divider()

    if df.empty:
        st.warning("⚠️ Dados não encontrados. Execute o pipeline de extração primeiro.")
        st.stop()

    # ================================
    # FILTROS
    # ================================
    st.sidebar.markdown(f"**📅 Mês de Referência:**\n\n*{data_ref}*")
    st.sidebar.header("🔍 Filtros do Painel")

    orgaos = ["Todos"] + sorted(df["Órgão de Exercício"].dropna().unique())
    orgao_selecionado = st.sidebar.selectbox("Órgão de Exercício:", orgaos)

    tem_funcao_opcoes = ["Todos", "Sim", "Não"]
    funcao_selecionada = st.sidebar.radio(
        "Ocupa Função Comissionada?",
        tem_funcao_opcoes
    )

    classes = ["Todas"] + sorted(
        df[df["Classe"] != "Desconhecida"]["Classe"].unique()
    )

    classe_selecionada = st.sidebar.selectbox(
        "Classe na Carreira:",
        classes
    )

    anos_validos = sorted(
        [ano for ano in df["Ano de Ingresso"].unique() if ano.isdigit()],
        reverse=True
    )

    anos = ["Todos"] + anos_validos

    ano_selecionado = st.sidebar.selectbox(
        "Ano de Ingresso (Serviço Público):",
        anos
    )

    # ================================
    # APLICAÇÃO DOS FILTROS
    # ================================
    df_filtrado = df.copy()

    if orgao_selecionado != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["Órgão de Exercício"] == orgao_selecionado
        ]

    if funcao_selecionada != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["Tem Função?"] == funcao_selecionada
        ]

    if classe_selecionada != "Todas":
        df_filtrado = df_filtrado[
            df_filtrado["Classe"] == classe_selecionada
        ]

    if ano_selecionado != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["Ano de Ingresso"] == ano_selecionado
        ]

    # ================================
    # KPIs
    # ================================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total de ATIs (Filtro)", len(df_filtrado))

    with col2:

        atis_func = len(df_filtrado[df_filtrado["Tem Função?"] == "Sim"])

        perc = (
            atis_func / len(df_filtrado) * 100
            if len(df_filtrado) > 0
            else 0
        )

        st.metric("Com Função", f"{atis_func} ({perc:.1f}%)")

    with col3:
        st.metric(
            "Órgãos Distintos",
            df_filtrado["Órgão de Exercício"].nunique()
        )

    with col4:

        if not df_filtrado.empty:
            ano_mais_comum = df_filtrado["Ano de Ingresso"].mode()[0]
        else:
            ano_mais_comum = "-"

        st.metric("Ano de Ingresso (Moda)", ano_mais_comum)

    st.divider()

    # ================================
    # GRÁFICOS
    # ================================
    colA, colB = st.columns(2)

    with colA:

        st.subheader("🏢 Top 10 Órgãos com mais ATIs")

        df_orgaos = (
            df_filtrado["Órgão de Exercício"]
            .value_counts()
            .reset_index()
            .head(10)
        )

        df_orgaos.columns = ["Órgão", "Quantidade"]

        fig_orgaos = px.bar(
            df_orgaos,
            x="Quantidade",
            y="Órgão",
            orientation="h",
            color="Quantidade",
            color_continuous_scale="Blues"
        )

        fig_orgaos.update_layout(
            yaxis={"categoryorder": "total ascending"}
        )

        st.plotly_chart(fig_orgaos, use_container_width=True)

    with colB:

        st.subheader("📊 Distribuição por Nível da Carreira")

        df_niveis = (
            df_filtrado
            .groupby(["Nível/Padrão", "Tem Função?"])
            .size()
            .reset_index(name="Quantidade")
        )

        df_niveis = df_niveis.sort_values(by="Nível/Padrão")

        fig_niveis = px.bar(
            df_niveis,
            x="Nível/Padrão",
            y="Quantidade",
            color="Tem Função?",
            barmode="stack",
            color_discrete_map={
                "Sim": "#1f77b4",
                "Não": "#ff7f0e"
            }
        )

        st.plotly_chart(fig_niveis, use_container_width=True)

    # ================================
    # TABELA
    # ================================
    st.subheader("📋 Tabela Analítica Detalhada")

    df_exibicao = df_filtrado.drop(
        columns=["Classe", "Ano de Ingresso"]
    )

    st.dataframe(
        df_exibicao,
        use_container_width=True,
        hide_index=True
    )

# ================================
# PÁGINA 2 - SOBRE A CARREIRA
# ================================
elif pagina == "📚 Sobre a Carreira":

    st.title("A Carreira de Analista em Tecnologia da Informação (ATI)")

    st.markdown(
        "### Principais pontos da Lei nº 14.875, de 31 de maio de 2024"
    )

    st.divider()

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
A remuneração da carreira é estruturada no modelo de **subsídio**, ou seja, uma parcela única mensal
definida pelo nível na carreira, sem gratificações incorporadas ao vencimento base.

Além do subsídio, o servidor tem direito a verbas indenizatórias, tais como:

- Auxílio-alimentação
- Auxílio-transporte
- Auxílio-saúde
- Auxílio pré-escolar
- 13º salário
- 1/3 constitucional de férias
        """)

        st.link_button(
            "💰 Acessar Simulador de Salário dos ATIs",
            "https://josebarbosa.com.br/simuladores/executivofederal/"
        )

    with st.expander("📈 Como funciona a progressão na carreira?"):
        st.markdown("""
### Progressão Funcional
Passagem de um **padrão para o seguinte dentro da mesma classe**.

Exemplo: A-I → A-II → A-III

**📜 Previsão na Lei nº 14.875/2024:** interstício mínimo de **12 meses**.

**⚠️ Situação atual (2026):** enquanto o regulamento específico não é publicado, o interstício praticado é de:
- **18 meses** para servidores sem função comissionada
- **12 meses** para servidores **ocupando função comissionada**

---

### Promoção
Passagem do **último padrão de uma classe para o primeiro padrão da classe seguinte**.

Exemplo: A-V → B-I

**📜 Previsão na Lei nº 14.875/2024:** interstício mínimo de **12 meses** no último padrão da classe.

**⚠️ Situação atual (2026):** mesmas regras transitórias aplicadas à progressão funcional (18 ou 12 meses conforme ocupação de função comissionada).
        """)

    with st.expander("🏛️ Requisitos para promoção (mudança de classe)"):
        st.write("""
De acordo com o **Art. 36 da Lei nº 14.875/2024**, a promoção ocorre quando o servidor cumpre,
simultaneamente, os seguintes requisitos:

1. Cumprimento do interstício mínimo no último padrão da classe atual
2. Avaliação de desempenho com resultado **satisfatório**
        """)

    with st.expander("🔄 Movimentação de servidores (Art. 38)"):
        st.write("""
Os servidores efetivos da carreira ATI **somente** poderão ser afastados ou cedidos nas seguintes hipóteses:

1. Requisição pela **Presidência ou Vice-Presidência da República**, ou nas hipóteses legais de requisição.
2. Cessão para órgãos ou entidades do **Poder Executivo Federal** para exercício de cargo em comissão (CCE) ou função de confiança (FCE) de **nível mínimo 13** ou equivalente.
3. Cessão para órgãos ou entidades de **outros Poderes da União** para exercício de CCE ou FCE de **nível mínimo 15** ou equivalente.
4. Cessão para exercício de **cargo de Secretário de Estado ou do Distrito Federal**, cargo equivalente ou superior ao CCE/FCE nível 15, ou dirigente máximo de entidade pública em: Estados, Distrito Federal, prefeituras de capitais ou municípios com **mais de 500.000 habitantes**.
        """)

    with st.expander("🏛️ Papel da Secretaria de Governo Digital (SGD)"):
        st.write("""
A carreira ATI está inserida no contexto da **governança digital do Poder Executivo Federal**.

A **Secretaria de Governo Digital (SGD)** é responsável por:

- Coordenar políticas de transformação digital e interoperabilidade de sistemas
- Gerir o **Sistema de Administração dos Recursos de Tecnologia da Informação (SISP)**, que organiza e integra as áreas de TI dos órgãos federais
- **Autorizar e gerir a movimentação dos servidores ATI** para atuação nos órgãos e entidades da Administração Pública Federal direta, autárquica e fundacional, integrantes ou não do SISP
        """)

        st.link_button(
            "🔗 Conhecer o SISP e a Secretaria de Governo Digital",
            "https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/sisp"
        )

    with st.expander("🤝 Associação da carreira (ANATI)"):
        st.write("""
A **Associação Nacional dos Analistas em Tecnologia da Informação (ANATI)** é a
entidade representativa da carreira de ATI.

A associação atua em diversas frentes:

- Defesa institucional da carreira
- Acompanhamento legislativo
- Articulação com órgãos do governo
- Produção de estudos e propostas sobre governança digital
- Apoio à valorização dos profissionais de TI do governo federal
        """)

        st.link_button(
            "🔗 Acessar o site da ANATI",
            "http://anati.org.br/"
        )

    st.divider()
    st.caption("Informações baseadas na Lei nº 14.875/2024 e nas práticas administrativas atuais da carreira ATI.")

# ================================
# RODAPÉ LATERAL (SEMPRE VISÍVEL)
# ================================
st.sidebar.divider()
st.sidebar.markdown("👨‍💻 **Feito por:** [Diego Martins](https://diegogyn.github.io/)")
st.sidebar.link_button("🐛 Dúvidas, Sugestões ou Erros", "https://github.com/diegogyn/ObservatorioATI/issues")