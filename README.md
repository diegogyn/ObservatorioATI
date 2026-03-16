# 💻 Observatório da Carreira ATI (Executivo Federal)

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=github-actions&logoColor=white)

Um painel interativo e automatizado para análise da distribuição dos **Analistas em Tecnologia da Informação (ATIs)** no Poder Executivo Federal. Este projeto consome dados abertos governamentais, realiza o processamento pesado de dados (ETL) e exibe métricas detalhadas através de um dashboard em tempo real.

---

## 🎯 Objetivo do Projeto

A carreira de ATI é transversal, o que significa que os servidores estão espalhados por diversos ministérios e autarquias. O objetivo deste Observatório é prover transparência e responder a perguntas como:
* Onde estão alocados os ATIs?
* Qual a proporção de servidores que ocupam Funções Comissionadas (CCE/FCE)?
* Qual a distribuição por Classe/Padrão e o histórico de ingressos no serviço público?

---

## ⚙️ Arquitetura e Engenharia de Dados

Para evitar lentidão na visualização e contornar limites de tamanho do GitHub (arquivos > 100MB), a arquitetura foi separada em duas camadas principais:

1. **Pipeline de ETL (Extração, Transformação e Carga):**
   * O script `etl_atis.py` consome o arquivo bruto compactado (`.zip`) de Servidores do SIAPE disponibilizado pelo Portal da Transparência (base com centenas de milhares de linhas).
   * Ele descompacta, varre o Big Data buscando especificamente o cargo de ATI, cruza os vínculos efetivos com os vínculos de chefia (para montar a sigla correta da função, ex: *CCE 1.13 - COORDENADOR-GERAL*), trata dados nulos/sujos e gera um arquivo leve (`dados_atis.csv`).
   * Também extrai metadados do nome do arquivo para identificar automaticamente o mês de referência.

2. **Dashboard Interativo (Streamlit):**
   * O aplicativo `app.py` lê os dados já mastigados, aplicando cache em memória para navegação super rápida.
   * Interface rica com gráficos Plotly e cruzamento dinâmico de filtros.

3. **Automação CI/CD (GitHub Actions):**
   * Sempre que um novo arquivo `.zip` é feito o upload no repositório, uma esteira automatizada roda o ETL na nuvem, commita os dados limpos e apaga o arquivo bruto pesado para poupar espaço.

---

## 🛠️ Como executar localmente

### 1. Pré-requisitos
Certifique-se de ter o [Python](https://www.python.org/downloads/) instalado na sua máquina.

### 2. Clonando e Configurando o Ambiente
Abra o terminal (CMD/PowerShell) e execute:

```bash
# Clone este repositório
git clone https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git
cd NOME_DO_REPOSITORIO

# Crie um ambiente virtual
python -m venv venv

# Ative o ambiente (No Windows)
venv\Scripts\activate
# (No Linux/Mac, use: source venv/bin/activate)

# Instale as dependências
pip install -r requirements.txt
```
### 3. Obtendo os Dados Brutos
Acesse o Portal da Transparência - Servidores.
Baixe o arquivo de Servidores SIAPE do mês mais recente (Ex: 202601_Servidores_SIAPE.zip).
Coloque este arquivo .zip inteiro dentro da pasta data/ do projeto.


### 4. Rodando o Pipeline e o Dashboard
```bash
# Execute o extrator de dados (limpeza e processamento)
python etl_atis.py

# Inicie a interface do Observatório
streamlit run app.py
```
O painel abrirá automaticamente no seu navegador em http://localhost:8501.

