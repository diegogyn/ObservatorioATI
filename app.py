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
# FUNÇÃO DE CARREGAMENTO DE DADOS
# ================================
@st.cache_data
def load_data():

    caminho_arquivo = os.path.join("data", "dados_atis.csv")
    caminho_meta = os.path.join("data", "metadata.json")
    caminho_desligamentos = os.path.join("data", "desligamentos-ati-pep-fev-2026.csv")

    data_ref = "Atualização Pendente"

    # Carrega Metadados
    if os.path.exists(caminho_meta):
        with open(caminho_meta, "r", encoding="utf-8") as f:
            data_ref = json.load(f).get("data_referencia", "Desconhecida")

    # Carrega Base Principal
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

        # EXTRAÇÃO INTELIGENTE: Focado 100% em FCE
        def classificar_funcao(funcao):
            funcao = str(funcao).strip().upper()
            if funcao in["SEM FUNÇÃO", "NAN", ""]:
                return "Sem Função", "Sem Função", "Sem Função", -1
                
            match = re.search(r'\b(FCE)\b.*?(?:[^\d]|^)(\d{2})\b', funcao)
            if match:
                tipo = match.group(1) 
                nivel = match.group(2)
                if nivel.isdigit() and 1 <= int(nivel) <= 17:
                    return f"FCE Nível {nivel}", "FCE", f"Nível {nivel}", int(nivel)
            
            return "Outras Funções", "Outras Funções", "Outras", 0

        if "Função" in df.columns:
            resultados = df["Função"].apply(classificar_funcao)
            df["Função Resumo"] =[res[0] for res in resultados]
            df["Tipo Função"] = [res[1] for res in resultados]
            df["Nível Função"] =[res[2] for res in resultados]
            df["Ordem Nível"] =[res[3] for res in resultados]
        else:
            df["Função Resumo"] = "Desconhecida"
            df["Tipo Função"] = "Desconhecida"
            df["Nível Função"] = "Desconhecida"
            df["Ordem Nível"] = -1

    # Carrega Dados de Desligamento
    try:
        # utf-8-sig ignora eventuais caracteres BOM invisíveis do Excel/CSV
        df_deslig = pd.read_csv(caminho_desligamentos, encoding="utf-8-sig")
        
        # Filtra sujeiras das últimas linhas (Aba, Selection Status, etc)
        df_deslig = df_deslig[df_deslig["Ano"].astype(str).str.isnumeric()]
        
        # Renomeia e tipa as colunas
        df_deslig = df_deslig.rename(columns={"Quantidade de Desligamentos": "Desligamentos"})
        df_deslig["Ano"] = df_deslig["Ano"].astype(str)
        df_deslig["Desligamentos"] = df_deslig["Desligamentos"].astype(int)
        df_deslig = df_deslig[["Ano", "Desligamentos"]]
    except FileNotFoundError:
        df_deslig = pd.DataFrame(columns=["Ano", "Desligamentos"])

    return df, data_ref, df_deslig


df, data_ref, df_deslig = load_data()

# ================================
# MENU LATERAL
# ================================
pagina = st.sidebar.radio(
    "📌 Navegação do Painel",["📊 Observatório ATI", "📚 Sobre a Carreira"]
)

st.sidebar.divider()

# ================================
# PÁGINA 1 - OBSERVATÓRIO
# ================================
if pagina == "📊 Observatório ATI":

    st.title("💻 Observatório da Carreira ATI")
    st.markdown("Painel interativo com a distribuição dos **Analistas em Tecnologia da Informação** do Executivo Federal.")
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

    tem_funcao_opcoes =["Todos", "Sim", "Não"]
    funcao_selecionada = st.sidebar.radio("Ocupa Função Comissionada?", tem_funcao_opcoes)

    classes = ["Todas"] + sorted(df[df["Classe"] != "Desconhecida"]["Classe"].unique())
    classe_selecionada = st.sidebar.selectbox("Classe na Carreira:", classes)

    anos_validos = sorted([ano for ano in df["Ano de Ingresso"].unique() if ano.isdigit()], reverse=True)
    anos = ["Todos"] + anos_validos
    ano_selecionado = st.sidebar.selectbox("Ano de Ingresso (Serviço Público):", anos)

    # ================================
    # APLICAÇÃO DOS FILTROS
    # ================================
    df_filtrado = df.copy()

    if orgao_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Órgão de Exercício"] == orgao_selecionado]
    if funcao_selecionada != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Tem Função?"] == funcao_selecionada]
    if classe_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Classe"] == classe_selecionada]
    if ano_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Ano de Ingresso"] == ano_selecionado]

    # ================================
    # KPIs
    # ================================
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total de ATIs (Filtro)", len(df_filtrado))
    with col2:
        atis_func = len(df_filtrado[df_filtrado["Tem Função?"] == "Sim"])
        perc = (atis_func / len(df_filtrado) * 100 if len(df_filtrado) > 0 else 0)
        st.metric("Com Função", f"{atis_func} ({perc:.1f}%)")
    with col3: st.metric("Órgãos Distintos", df_filtrado["Órgão de Exercício"].nunique())
    with col4:
        ano_mais_comum = df_filtrado["Ano de Ingresso"].mode()[0] if not df_filtrado.empty else "-"
        st.metric("Ano de Ingresso (Moda)", ano_mais_comum)

    st.divider()

    # ================================
    # GRÁFICOS PARTE 1
    # ================================
    colA, colB = st.columns(2)

    with colA:
        st.subheader("🏢 Top 10 Órgãos com mais ATIs")
        
        top_10_nomes = df_filtrado["Órgão de Exercício"].value_counts().head(10).index.tolist()
        df_top10 = df_filtrado[df_filtrado["Órgão de Exercício"].isin(top_10_nomes)]
        df_orgaos_func = df_top10.groupby(["Órgão de Exercício", "Tem Função?"]).size().reset_index(name="Quantidade")
        
        fig_orgaos = px.bar(
            df_orgaos_func, 
            x="Quantidade", 
            y="Órgão de Exercício", 
            color="Tem Função?", 
            orientation="h",
            color_discrete_map={"Sim": "#1f77b4", "Não": "#b0c4de"}, 
            category_orders={"Órgão de Exercício": top_10_nomes[::-1]} 
        )
        fig_orgaos.update_layout(barmode="stack", margin=dict(t=20, b=20, l=0, r=0))
        st.plotly_chart(fig_orgaos, use_container_width=True)

    with colB:
        st.subheader("📊 Distribuição por Nível da Carreira")
        
        modo_percentual = st.toggle("Ver em Percentual (%)", value=False)
        
        df_niveis = df_filtrado.groupby(["Nível/Padrão", "Tem Função?"]).size().reset_index(name="Quantidade")
        df_niveis = df_niveis.sort_values(by="Nível/Padrão")
        
        barmode_tipo = "relative" if modo_percentual else "stack"
        barnorm_tipo = "percent" if modo_percentual else None
        
        fig_niveis = px.bar(
            df_niveis, 
            x="Nível/Padrão", 
            y="Quantidade", 
            color="Tem Função?", 
            color_discrete_map={"Sim": "#1f77b4", "Não": "#ff7f0e"}
        )
        fig_niveis.update_layout(
            barmode=barmode_tipo, 
            barnorm=barnorm_tipo,
            yaxis_title="% de Servidores" if modo_percentual else "Quantidade"
        )
        st.plotly_chart(fig_niveis, use_container_width=True)

    st.divider()

    # ================================
    # GRÁFICOS PARTE 1.5 - TEMPO E SENIORIDADE
    # ================================
    colC, colD = st.columns(2)

    with colC:
        st.subheader("⏳ Histórico de Ingresso (Filtro Atual)")
        st.markdown("Distribuição do ano de ingresso no serviço público.")
        
        df_anos = df_filtrado[df_filtrado["Ano de Ingresso"] != "Desconhecido"]
        if not df_anos.empty:
            df_ingressos = df_anos.groupby("Ano de Ingresso").size().reset_index(name="Quantidade")
            df_ingressos = df_ingressos.sort_values("Ano de Ingresso")
            
            fig_anos = px.line(
                df_ingressos, x="Ano de Ingresso", y="Quantidade", 
                markers=True, text="Quantidade",
                color_discrete_sequence=["#d62728"]
            )
            fig_anos.update_traces(textposition="top center")
            fig_anos.update_layout(yaxis_title="Qtd de Ingressos", xaxis_title="Ano")
            st.plotly_chart(fig_anos, use_container_width=True)
        else:
            st.info("Sem dados de ingresso no filtro atual.")

    with colD:
        st.subheader("⭐ Senioridade na Carreira (Por Classe)")
        st.markdown("Distribuição macro dos servidores pelas classes (A, B, C, Especial).")
        
        df_classes = df_filtrado[df_filtrado["Classe"] != "Desconhecida"]
        if not df_classes.empty:
            ordem_classes =["A", "B", "C", "ESPECIAL"]
            df_cnt_classes = df_classes.groupby("Classe").size().reset_index(name="Quantidade")
            df_cnt_classes["Classe"] = pd.Categorical(df_cnt_classes["Classe"], categories=ordem_classes, ordered=True)
            df_cnt_classes = df_cnt_classes.sort_values("Classe")

            fig_classes = px.pie(
                df_cnt_classes, 
                values="Quantidade", 
                names="Classe",
                hole=0.3,
                color="Classe",
                color_discrete_map={"A": "#17becf", "B": "#9467bd", "C": "#e377c2", "ESPECIAL": "#bcbd22"}
            )
            fig_classes.update_traces(textinfo='percent+value+label', textposition='inside')
            fig_classes.update_layout(showlegend=False, margin=dict(t=20, b=20, l=0, r=0))
            st.plotly_chart(fig_classes, use_container_width=True)

    # ================================
    # GRÁFICOS PARTE 1.8 - BALANÇO DE PESSOAL (GLOBAL)
    # ================================
    st.divider()
    st.subheader("⚖️ Balanço da Carreira (Visão Global: Ingressos vs Evasão)")
    st.markdown("Comparativo histórico entre a entrada de novos servidores e a perda por desligamentos. *Nota: Os desligamentos não possuem detalhamento por órgão/classe, portanto esta seção representa o **cenário geral da carreira** e não sofre alteração dos filtros laterais.*")

    if not df_deslig.empty:
        # Pega todos os ingressos globais
        df_ingressos_global = df[df["Ano de Ingresso"] != "Desconhecido"].groupby("Ano de Ingresso").size().reset_index(name="Ingressos")
        df_ingressos_global = df_ingressos_global.rename(columns={"Ano de Ingresso": "Ano"})

        # Mescla Ingressos e Desligamentos usando o Ano
        df_balanco = pd.merge(df_ingressos_global, df_deslig, on="Ano", how="outer").fillna(0)
        df_balanco["Ingressos"] = df_balanco["Ingressos"].astype(int)
        df_balanco["Desligamentos"] = df_balanco["Desligamentos"].astype(int)
        df_balanco = df_balanco.sort_values("Ano")
        
        # Filtra a partir do primeiro ano que faz sentido mostrar (ex: 2010 pra frente)
        df_balanco = df_balanco[df_balanco["Ano"].astype(int) >= 2010]

        # --- NOVOS KPIs ---
        total_desligamentos = df_balanco["Desligamentos"].sum()
        st.metric("Total de Evasão (Desde 2010)", f"{total_desligamentos}")

        st.write("") # Espaçamento
        
        # Derrete (Melt) o dataframe para o Plotly plotar barras agrupadas facilmente
        df_melted = df_balanco.melt(id_vars="Ano", value_vars=["Ingressos", "Desligamentos"], var_name="Movimentação", value_name="Quantidade")

        # Gráfico ocupando a largura total agora
        fig_balanco = px.bar(
            df_melted, x="Ano", y="Quantidade", color="Movimentação", barmode="group",
            color_discrete_map={"Ingressos": "#1f77b4", "Desligamentos": "#d62728"}, # Azul e Vermelho
            text_auto=True
        )
        fig_balanco.update_layout(yaxis_title="Qtd. de Servidores", xaxis_title="Ano do Evento", margin=dict(t=20, b=20))
        fig_balanco.update_traces(textposition='outside')
        st.plotly_chart(fig_balanco, use_container_width=True)
    else:
        st.info("Nenhum dado de evasão encontrado. Adicione o arquivo 'desligamentos-ati-pep-fev-2026.csv' na pasta 'data'.")

    # --- NOVO BLOCO DE TEXTO ANALÍTICO ---
    st.warning("""
    **⚠️ O Risco da Estagnação para o Estado Brasileiro**
        
    O cenário ilustrado pelo balanço acima evidencia um déficit crítico: a retenção e o crescimento da força de trabalho de ATIs não acompanharam a explosão da demanda por tecnologia no setor público. 
        
    Essa realidade compromete diretamente a **Estratégia de Governo Digital** e coloca o país em uma posição de vulnerabilidade tecnológica. O baixo crescimento do quadro efetivo gera impactos severos e **prejuízos diretos à Administração Pública**, tais como:

    * **Dependência e Custos Elevados:** A incapacidade de absorver e reter talentos obriga o governo a recorrer excessivamente a contratos de terceirização e consultorias, encarecendo a gestão de TI e dificultando a fiscalização técnica e isenta dos serviços prestados.
    * **Perda de Memória Institucional (Fuga de Cérebros):** A alta evasão significa que o conhecimento profundo sobre a arquitetura de sistemas críticos e bases de dados nacionais é constantemente perdido, gerando retrabalho e ineficiência.
    * **Atraso na Inovação e Descontinuidade:** Projetos estruturantes de transformação digital, adoção de inteligência artificial e unificação de serviços sofrem com a falta de liderança técnica permanente.
    * **Riscos à Segurança e Soberania Nacional:** A fragilização do quadro próprio de especialistas em TI amplia os riscos de incidentes cibernéticos e compromete a soberania do Estado na governança dos dados dos cidadãos.
        
    Em suma, sem políticas de valorização, atração e expansão robusta da carreira de ATI, o Estado perde sua capacidade de resposta frente aos desafios tecnológicos modernos, ameaçando a continuidade e a qualidade da cidadania digital no Brasil.
    """)

    # ================================
    # GRÁFICOS PARTE 2: Foco nas FCEs
    # ================================
    st.divider()
    st.subheader("🎯 Raio-X das Funções Comissionadas Executivas (FCE)")
    
    st.info("💡 **Como ler este gráfico?** Foram grupadas as funções FCE pelos seus **dois últimos dígitos (ex: 05, 10, 13)**, que representam o nível da função. Demais tipos de função foram alocados em 'Outras Funções'.")

    col_Dnt, col_Bar = st.columns([1, 2])

    cores_map = {"FCE": "#2CA02C", "Outras Funções": "#9467BD", "Sem Função": "#7F7F7F"}

    with col_Dnt:
        st.markdown("**Proporção de Vínculos de Chefia/Assessoramento**")
        df_pizza = df_filtrado[df_filtrado["Tipo Função"] != "Sem Função"]["Tipo Função"].value_counts().reset_index()
        df_pizza.columns =["Tipo", "Quantidade"]
        
        if not df_pizza.empty:
            fig_pizza = px.pie(df_pizza, values="Quantidade", names="Tipo", hole=0.45, color="Tipo", color_discrete_map=cores_map)
            fig_pizza.update_traces(textposition='inside', textinfo='percent+label')
            fig_pizza.update_layout(showlegend=False, margin=dict(t=20, b=20, l=0, r=0))
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.warning("Sem dados de função para exibir.")

    with col_Bar:
        st.markdown("**Distribuição por Nível da Função (FCE 01 ao 17)**")
        
        df_fce = df_filtrado[df_filtrado["Tipo Função"] == "FCE"]
        
        if not df_fce.empty:
            df_bar = df_fce.groupby(["Nível Função", "Ordem Nível"]).size().reset_index(name="Quantidade")
            df_bar = df_bar.sort_values(by="Ordem Nível")

            fig_bar = px.bar(
                df_bar, x="Nível Função", y="Quantidade", 
                text="Quantidade", color_discrete_sequence=["#2CA02C"]
            )
            fig_bar.update_traces(textposition='outside')
            fig_bar.update_layout(xaxis_title="", yaxis_title="Quantidade de Servidores", margin=dict(t=20, b=20))
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Nenhum servidor FCE no filtro atual.")

    # ================================
    # TABELA FINAL
    # ================================
    st.divider()
    st.subheader("📋 Base de Dados Completa")

    df_exibicao = df_filtrado.drop(columns=["Classe", "Ano de Ingresso", "Ordem Nível", "Tipo Função", "Nível Função"], errors="ignore")
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

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

    with st.expander("💼 Valores Oficiais (FCE)"):
        st.markdown("""
Abaixo constam as tabelas exatas de remuneração da **Função Comissionada Executiva (FCE)**.
        """)
                # DADOS BRUTOS EXATOS FCE
        dados_raw_fce = """Cargo/Função	Valor	CCE Unitário
FCE 1 17	R$ 16.765,90	4,79
FCE 1 16	R$ 14.045,67	4,01
FCE 1 15	R$ 12.196,47	3,49
FCE 1 14	R$ 10.432,37	2,98
FCE 1 13	R$ 8.651,81	2,47
FCE 1 12	R$ 6.513,87	1,86
FCE 1 11	R$ 5.193,87	1,48
FCE 1 10	R$ 4.455,87	1,27
FCE 1 09	R$ 3.498,47	1,00
FCE 1 08	R$ 3.356,01	0,96
FCE 1 07	R$ 2.908,64	0,83
FCE 1 06	R$ 2.463,00	0,70
FCE 1 05	R$ 2.099,09	0,60
FCE 1 04	R$ 1.553,73	0,44
FCE 1 03	R$ 1.294,43	0,37
FCE 1 02	R$ 723,98	0,21
FCE 1 01	R$ 428,38	0,12
FCE 2 17	R$ 16.765,90	4,79
FCE 2 16	R$ 14.045,67	4,01
FCE 2 15	R$ 12.196,47	3,49
FCE 2 14	R$ 10.432,37	2,98
FCE 2 13	R$ 8.651,81	2,47
FCE 2 12	R$ 6.513,87	1,86
FCE 2 11	R$ 5.193,87	1,48
FCE 2 10	R$ 4.455,87	1,27
FCE 2 09	R$ 3.498,47	1,00
FCE 2 08	R$ 3.356,01	0,96
FCE 2 07	R$ 2.908,64	0,83
FCE 2 06	R$ 2.463,00	0,70
FCE 2 05	R$ 2.099,09	0,60
FCE 2 04	R$ 1.553,73	0,44
FCE 2 03	R$ 1.294,43	0,37
FCE 2 02	R$ 723,98	0,21
FCE 2 01	R$ 428,38	0,12
FCE 3 16	R$ 14.045,67	4,01
FCE 3 15	R$ 12.196,47	3,49
FCE 3 14	R$ 10.432,37	2,98
FCE 3 13	R$ 8.651,81	2,47
FCE 3 12	R$ 6.513,87	1,86
FCE 3 11	R$ 5.193,87	1,48
FCE 3 10	R$ 4.455,87	1,27
FCE 3 09	R$ 3.498,47	1,00
FCE 3 08	R$ 3.356,01	0,96
FCE 3 07	R$ 2.908,64	0,83
FCE 3 06	R$ 2.463,00	0,70
FCE 3 05	R$ 2.099,09	0,60
FCE 3 04	R$ 1.553,73	0,44
FCE 3 03	R$ 1.294,43	0,37
FCE 3 02	R$ 723,98	0,21
FCE 3 01	R$ 428,38	0,12
FCE 4 13	R$ 8.651,81	2,47
FCE 4 12	R$ 6.513,87	1,86
FCE 4 11	R$ 5.193,87	1,48
FCE 4 10	R$ 4.455,87	1,27
FCE 4 09	R$ 3.498,47	1,00
FCE 4 08	R$ 3.356,01	0,96
FCE 4 07	R$ 2.908,64	0,83
FCE 4 06	R$ 2.463,00	0,70
FCE 4 05	R$ 2.099,09	0,60
FCE 4 04	R$ 1.553,73	0,44
FCE 4 03	R$ 1.294,43	0,37
FCE 4 02	R$ 723,98	0,21
FCE 4 01	R$ 428,38	0,12"""

        df_fce = pd.read_csv(io.StringIO(dados_raw_fce), sep="\t")
        st.dataframe(df_fce, hide_index=True, use_container_width=True)

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