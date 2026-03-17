import pandas as pd
import glob
import os
import zipfile
import json
import re

def extrair_data_arquivo(nome_arquivo):
    match = re.search(r'(\d{4})(\d{2})', nome_arquivo)
    if match:
        ano = match.group(1)
        mes_num = match.group(2)
        meses = {
            "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
            "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
            "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
        }
        return f"{meses.get(mes_num, 'Mês Indefinido')} de {ano}"
    return "Data não identificada"

def processar_dados_abertos():
    print("🚀 Iniciando o ETL do Governo Federal...\n")
    
    os.makedirs("data", exist_ok=True)
    arquivo_base = None

    arquivos_zip = glob.glob(os.path.join("data", "*.zip"))
    if arquivos_zip:
        print(f"📦 Arquivo ZIP encontrado: {arquivos_zip[0]}. Extraindo...")
        with zipfile.ZipFile(arquivos_zip[0], 'r') as z:
            alvo = next((f for f in z.namelist() if f.endswith('_Cadastro.csv')), None)
            if alvo:
                z.extract(alvo, "data")
                arquivo_base = os.path.join("data", alvo)
                print(f"✅ Arquivo {alvo} extraído com sucesso!")

    if not arquivo_base:
        arquivos_csv = glob.glob(os.path.join("data", "*_Cadastro.csv"))
        if arquivos_csv:
            arquivo_base = arquivos_csv[0]
        else:
            print("❌ Nenhum arquivo ZIP ou CSV encontrado.")
            return

    data_atualizacao = extrair_data_arquivo(os.path.basename(arquivo_base))
    with open(os.path.join("data", "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"data_referencia": data_atualizacao}, f, ensure_ascii=False)

    print(f"📅 Data Base Identificada: {data_atualizacao}")
    print("⏳ Aguarde, processando os dados (Cerca de 1 minuto)...")

    # A base do governo usa 'iso-8859-1' ou 'latin1' (isso já corrige 99% dos acentos automaticamente)
    df = pd.read_csv(arquivo_base, sep=';', encoding='iso-8859-1', low_memory=False, dtype=str)
    
    # Padroniza as colunas
    df.columns = [str(c).upper().strip() for c in df.columns]

    # Busca das colunas exatas
    col_id = 'ID_SERVIDOR_PORTAL'
    col_nome = 'NOME'
    col_cargo = 'DESCRICAO_CARGO'
    col_classe = 'CLASSE_CARGO'
    col_padrao = 'PADRAO_CARGO'
    col_sigla = 'SIGLA_FUNCAO'
    col_nivel_func = 'NIVEL_FUNCAO'
    col_atividade = 'ATIVIDADE'
    col_orgao = 'ORG_EXERCICIO'
    
    col_data_sp = 'DATA_DIPLOMA_INGRESSO_SERVICOPUBLICO'
    col_data_funcao = 'DATA_INGRESSO_CARGOFUNCAO'

    filtro_ati = df[col_cargo].astype(str).str.contains("ANALISTA EM TECNOL DA INFORMACAO", case=False, na=False)
    
    if col_id in df.columns:
        identificadores_atis = df[filtro_ati][col_id].unique()
        chave_agrupamento = col_id
    else:
        identificadores_atis = df[filtro_ati][col_nome].unique()
        chave_agrupamento = col_nome

    if len(identificadores_atis) == 0:
        print("⚠️ Nenhum ATI encontrado! Verifique a codificação do arquivo.")
        return

    df_atis_completo = df[df[chave_agrupamento].isin(identificadores_atis)]
    dados_processados = []

    for identificador, group in df_atis_completo.groupby(chave_agrupamento):
        linhas_efetivas = group[group[col_cargo].astype(str).str.contains("ANALISTA EM TECNOL DA INFORMACAO", case=False, na=False)]
        if linhas_efetivas.empty: continue
            
        linha_efetiva = linhas_efetivas.iloc[0]
        nome = str(linha_efetiva[col_nome]).strip()
        orgao = str(linha_efetiva[col_orgao]).strip().upper()
        
        romano = {"1": "I", "01": "I", "001": "I",
                "2": "II", "02": "II", "002": "II",
                "3": "III", "03": "III", "003": "III",
                "4": "IV", "04": "IV", "004": "IV",
                "5": "V", "05": "V", "005": "V",
                "6": "VI", "06": "VI", "006": "VI"}

        limites_validos = {
            "A": ["I", "II", "III", "IV", "V"],
            "B": ["I", "II", "III", "IV", "V", "VI"],
            "C": ["I", "II", "III", "IV", "V", "VI"],
            "ESPECIAL": ["I", "II", "III"],
        }

        classe_raw = str(linha_efetiva[col_classe]).strip().upper() if pd.notna(linha_efetiva[col_classe]) else '-'
        padrao_raw = str(linha_efetiva[col_padrao]).strip() if pd.notna(linha_efetiva[col_padrao]) else '-'
        padrao_fmt = romano.get(padrao_raw, padrao_raw)

        # Validação: marca dado suspeito para investigação
        padroes_validos = limites_validos.get(classe_raw, [])
        if padroes_validos and padrao_fmt not in padroes_validos:
            padrao_fmt = f"{padrao_fmt}(?)"  # sinaliza dado inconsistente

        classe_fmt = classe_raw.capitalize()
        nivel_padrao = f"{classe_fmt}-{padrao_fmt}"
                
        data_ingresso_sp = str(linha_efetiva[col_data_sp]).strip()
        if data_ingresso_sp in ['nan', '-1', '0', 'SEM INFORMAÇÃO', '']: data_ingresso_sp = "Não informada"
        
        funcao_final = "Sem Função"
        data_ingresso_funcao = "Não informada"
        
        for _, linha in group.iterrows():
            cargo_da_linha = str(linha[col_cargo]).strip().upper()
            tipo_vinculo = str(linha.get('COD_TIPO_VINCULO', '2')).strip()

            # Pula linhas que não são de função (tipo_vinculo != "1") e não são do cargo efetivo
            if tipo_vinculo != '1':
                continue  # só processa linhas de função
            
            if "ANALISTA EM TECNOL DA INFORMACAO" not in cargo_da_linha and cargo_da_linha not in ['-1', '0', 'NAN', '']:
                
                sigla = str(linha[col_sigla]).strip().upper() if pd.notna(linha[col_sigla]) else ""
                nivel = str(linha[col_nivel_func]).strip() if pd.notna(linha[col_nivel_func]) else ""
                atividade = str(linha[col_atividade]).strip().upper() if pd.notna(linha[col_atividade]) else ""
                
                # Filtra valores inválidos de forma robusta (cobre acentos e variações)
                if not sigla or sigla.startswith('-') or sigla.startswith('0') or 'INFORMA' in sigla:
                    sigla = ""
                if not nivel or nivel.startswith('-') or nivel == '0':
                    nivel = ""
                if not atividade or atividade.startswith('-') or atividade.startswith('0') or 'INFORMA' in atividade:
                    atividade = ""      
                
                partes_funcao = []
                
                if sigla:
                    sigla_limpa = sigla.replace("-", " ").split()[0]
                    if sigla_limpa == "FEX": sigla_limpa = "FCE"
                    
                    nivel_limpo = nivel.lstrip('0')
                    
                    if len(nivel_limpo) == 3 and nivel_limpo.isdigit():
                        nivel_limpo = f"{nivel_limpo[0]}.{nivel_limpo[1:]}"
                    elif len(nivel_limpo) == 4 and nivel_limpo.isdigit():
                        nivel_limpo = f"{nivel_limpo[:3]}.{nivel_limpo[3:]}"
                        
                    if nivel_limpo:
                        partes_funcao.append(f"{sigla_limpa} {nivel_limpo}")
                    else:
                        partes_funcao.append(sigla_limpa)
                
                if atividade:
                    partes_funcao.append(atividade)
                
                if partes_funcao:
                    funcao_final = " - ".join(partes_funcao)
                    
                    orgao_chefia = str(linha[col_orgao]).strip().upper()
                    if orgao_chefia not in ['-1', '0', 'NAN', 'SEM INFORMAÇÃO']:
                        orgao = orgao_chefia
                                            
                    dt_func = str(linha[col_data_funcao]).strip()
                    if dt_func not in ['nan', '-1', '0', 'SEM INFORMAÇÃO', '']: data_ingresso_funcao = dt_func
                    
                    break

        dados_processados.append({
            'Nome': nome,
            'Órgão de Exercício': orgao,
            'Nível/Padrão': nivel_padrao,
            'Função': funcao_final,
            'Tem Função?': 'Sim' if funcao_final != "Sem Função" else 'Não',
            'Ingresso Serviço Público': data_ingresso_sp,
            'Ingresso na Função': data_ingresso_funcao if funcao_final != "Sem Função" else "-"
        })

    df_final = pd.DataFrame(dados_processados)
    df_final.to_csv(os.path.join("data", "dados_atis.csv"), index=False, encoding="utf-8")
    print(f"\n✅ ETL Finalizado! {len(df_final)} ATIs estruturados com precisão.")

if __name__ == "__main__":
    processar_dados_abertos()