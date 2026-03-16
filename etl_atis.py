import pandas as pd
import glob
import os
import zipfile
import json
import re

def extrair_data_arquivo(nome_arquivo):
    # Procura um padrão de 6 números (ex: 202601) no nome do arquivo
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

    # 1. Checa se tem um arquivo ZIP (Ideal para o GitHub por causa do limite de 100MB)
    arquivos_zip = glob.glob(os.path.join("data", "*.zip"))
    if arquivos_zip:
        print(f"📦 Arquivo ZIP encontrado: {arquivos_zip[0]}. Extraindo...")
        with zipfile.ZipFile(arquivos_zip[0], 'r') as z:
            alvo = next((f for f in z.namelist() if f.endswith('_Cadastro.csv')), None)
            if alvo:
                z.extract(alvo, "data")
                arquivo_base = os.path.join("data", alvo)
                print(f"✅ Arquivo {alvo} extraído com sucesso!")

    # Se não tinha ZIP, procura direto o CSV
    if not arquivo_base:
        arquivos_csv = glob.glob(os.path.join("data", "*_Cadastro.csv"))
        if arquivos_csv:
            arquivo_base = arquivos_csv[0]
        else:
            print("❌ Nenhum arquivo ZIP ou CSV de Cadastro encontrado na pasta 'data'.")
            return

    # 2. Extrai a Data de Atualização do nome do arquivo
    data_atualizacao = extrair_data_arquivo(os.path.basename(arquivo_base))
    with open(os.path.join("data", "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"data_referencia": data_atualizacao}, f, ensure_ascii=False)

    print(f"📅 Data Base Identificada: {data_atualizacao}")
    print("⏳ Aguarde, processando os dados (Cerca de 1 minuto)...")

    # 3. Carrega a base
    df = pd.read_csv(arquivo_base, sep=';', encoding='iso-8859-1', low_memory=False, dtype=str)
    df.columns = [str(c).upper().strip() for c in df.columns]

    # 4. Mapeamento
    col_orgao = next((c for c in df.columns if c in['NOME_ORG_EXERCICIO', 'ORG_EXERCICIO', 'NOME_ORGSUP_EXERCICIO']), None)
    if not col_orgao: col_orgao = next((c for c in df.columns if 'EXERCICIO' in c and 'COD' not in c and 'ID' not in c and 'ORG' in c), None)

    col_nome = next((c for c in df.columns if c == 'NOME'), None)
    col_cargo = next((c for c in df.columns if 'CARGO' in c and 'DESC' in c), None)
    col_classe = next((c for c in df.columns if 'CLASSE' in c), None)
    col_padrao = next((c for c in df.columns if 'PADRAO' in c or 'PADRÃO' in c), None)
    col_id = next((c for c in df.columns if 'ID_SERVIDOR' in c), None)
    
    col_sigla = next((c for c in df.columns if 'SIGLA' in c and 'FUNC' in c), None)
    col_nivel_func = next((c for c in df.columns if 'NIVEL' in c and 'FUNC' in c), None)
    col_atividade = next((c for c in df.columns if ('ATIVIDADE' in c or 'FUNCAO' in c) and 'DESC' in c and 'COD' not in c), None)
    if not col_atividade:
        col_atividade = next((c for c in df.columns if 'ATIVIDADE' in c and 'COD' not in c and 'ID' not in c), None)

    col_data_sp = next((c for c in df.columns if 'DATA' in c and 'INGRESSO' in c and 'PUBLICO' in c), None)
    if not col_data_sp: col_data_sp = next((c for c in df.columns if 'DATA' in c and 'INGRESSO' in c and 'ORGAO' in c), None)
    col_data_funcao = next((c for c in df.columns if 'DATA' in c and 'INGRESSO' in c and ('FUNC' in c or 'CARGOFUNCAO' in c)), None)

    # 5. Processamento dos ATIs
    filtro_ati = df[col_cargo].astype(str).str.contains("ANALISTA EM TECNOL DA INFORMACAO", case=False, na=False)
    chave_agrupamento = col_id if col_id else col_nome
    identificadores_atis = df[filtro_ati][chave_agrupamento].unique()

    df_atis_completo = df[df[chave_agrupamento].isin(identificadores_atis)]
    dados_processados =[]

    for identificador, group in df_atis_completo.groupby(chave_agrupamento):
        linhas_efetivas = group[group[col_cargo].astype(str).str.contains("ANALISTA EM TECNOL DA INFORMACAO", case=False, na=False)]
        if linhas_efetivas.empty: continue
            
        linha_efetiva = linhas_efetivas.iloc[0]
        nome = str(linha_efetiva[col_nome]).strip() if col_nome else str(identificador)
        orgao = str(linha_efetiva[col_orgao]).strip() if col_orgao else "Não informado"
        
        classe = str(linha_efetiva[col_classe]).strip() if col_classe and pd.notna(linha_efetiva[col_classe]) else '-'
        padrao = str(linha_efetiva[col_padrao]).strip() if col_padrao and pd.notna(linha_efetiva[col_padrao]) else '-'
        nivel_padrao = f"Classe {classe} / Padrão {padrao}"
        
        data_ingresso_sp = str(linha_efetiva[col_data_sp]).strip() if col_data_sp and pd.notna(linha_efetiva[col_data_sp]) else "Não informada"
        if data_ingresso_sp in['nan', '-1', '0', 'SEM INFORMAÇÃO', '']: data_ingresso_sp = "Não informada"
        
        funcao_final = "Sem Função"
        data_ingresso_funcao = "Não informada"
        
        for _, linha in group.iterrows():
            sigla = str(linha[col_sigla]).strip() if col_sigla and pd.notna(linha[col_sigla]) else ""
            nivel = str(linha[col_nivel_func]).strip() if col_nivel_func and pd.notna(linha[col_nivel_func]) else ""
            atividade = str(linha[col_atividade]).strip() if col_atividade and pd.notna(linha[col_atividade]) else ""
            
            if sigla in['-1', '0', '0000', 'nan', 'SEM INFORMAÇÃO']: sigla = ""
            if nivel in['-1', '0', '0000', 'nan', 'SEM INFORMAÇÃO']: nivel = ""
            if atividade in['-1', '0', '0000', 'nan', 'SEM INFORMAÇÃO']: atividade = ""
            
            if sigla or atividade:
                partes_funcao = []
                
                # Formata a sigla e o nível
                if sigla:
                    sigla_limpa = sigla.upper().replace("FEX", "FCE") # Ajusta nomenclaturas legadas se necessário
                    nivel_limpo = nivel.lstrip('0') # Remove zeros à esquerda (ex: 0407 vira 407)
                    
                    # Se o nível for numérico longo, tenta colocar um ponto (ex: 407 -> 4.07, 117 -> 1.17)
                    if len(nivel_limpo) == 3:
                        nivel_limpo = f"{nivel_limpo[0]}.{nivel_limpo[1:]}"
                        
                    partes_funcao.append(f"{sigla_limpa} {nivel_limpo}".strip())
                    
                # Adiciona a descrição da atividade (o cargo em si)
                if atividade: 
                    partes_funcao.append(atividade.upper())
                
                funcao_final = " - ".join(partes_funcao)
                
                orgao_exercicio_funcao = linha[col_orgao] if col_orgao else None
                if pd.notna(orgao_exercicio_funcao) and str(orgao_exercicio_funcao).strip() not in['', '-1', '0', 'nan', 'SEM INFORMAÇÃO']:
                    orgao = str(orgao_exercicio_funcao).strip()
                
                dt_func = str(linha[col_data_funcao]).strip() if col_data_funcao and pd.notna(linha[col_data_funcao]) else "Não informada"
                if dt_func not in['nan', '-1', '0', 'SEM INFORMAÇÃO', '']: data_ingresso_funcao = dt_func
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
    print("\n✅ ETL Finalizado com Sucesso! Preparado para o Dashboard.")

if __name__ == "__main__":
    processar_dados_abertos()