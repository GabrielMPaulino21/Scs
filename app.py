import streamlit as st
import pandas as pd
import io
import os
from openpyxl import load_workbook
from openpyxl.styles import Border, Side, Alignment, Font, PatternFill

# --- 1. CONFIGURAÇÃO DA PÁGINA E DO ARQUIVO MESTRE ---
st.set_page_config(
    page_title="FollowUP-GY Automação",
    page_icon="🤖",
    layout="wide"
)

# !!! IMPORTANTE !!!
# SUBSTITUA PELA URL RAW DO SEU ARQUIVO NO GITHUB.
# Vá no seu GitHub -> Clique no arquivo -> Clique em "Raw". Copie a URL.
URL_ARQUIVO_GESTAO_RAW = "https://raw.githubusercontent.com/GabrielMPaulino21/Scs/main/Gest%C3%A3o%20de%20SC%20em%20aberto%20-%20Engenharia%20de%20Projetos.xlsx"


# --- 2. FUNÇÃO PRINCIPAL QUE REPLICA SUA LÓGICA DE SUCESSO ---

def executar_atualizacao_cirurgica(upload_cji5, upload_srm, upload_lcp, url_gestao):
    """
    Esta é a função principal. Ela combina a consolidação de dados
    com a atualização célula por célula para preservar a formatação.
    """
    
    # --- ETAPA 1: Processar e consolidar os 3 arquivos de entrada ---
    progress_bar = st.progress(0, text="▶️ Etapa 1/4: Lendo arquivos de entrada...")
    try:
        df_cji5 = pd.read_excel(upload_cji5)
        df_srm = pd.read_excel(upload_srm)
        df_lcp = pd.read_excel(upload_lcp, sheet_name='Capex', header=3, dtype={'WBS': str})
    except Exception as e:
        st.error(f"ERRO ao ler os arquivos de upload: {e}"); return None

    # Lógica de consolidação (baseada no seu Planilhas.py)
    df_cji5['Nº doc.de referência'] = df_cji5['Nº doc.de referência'].astype(str)
    df_cji5 = df_cji5[df_cji5['Nº doc.de referência'].str.startswith('S', na=False)].copy()
    if df_cji5.empty:
        st.warning("Nenhuma SC (iniciada com 'S') encontrada no arquivo Cji5."); return None

    df_cji5['SC_ID_Key'] = df_cji5['Nº doc.de referência'].str.replace('S', '', n=1, regex=False).str.strip()
    df_cji5['SC_ID_Key'] = pd.to_numeric(df_cji5['SC_ID_Key'], errors='coerce')
    df_cji5.dropna(subset=['SC_ID_Key'], inplace=True)
    df_cji5['SC_ID_Key'] = df_cji5['SC_ID_Key'].astype(int).astype(str)
    
    coluna_valor_correta = 'Valor/moed.transação'
    if coluna_valor_correta not in df_cji5.columns:
        st.error(f"ERRO: A coluna '{coluna_valor_correta}' não foi encontrada no Cji5."); return None
    df_cji5[coluna_valor_correta] = pd.to_numeric(df_cji5[coluna_valor_correta], errors='coerce').fillna(0)
    
    agg_funcs = {'Material': lambda x: ';\n'.join(x.dropna().astype(str).unique()),'Denominação': lambda x: ';\n'.join(x.dropna().astype(str).unique()),'Quantidade total': lambda x: ';\n'.join(x.dropna().astype(str)),coluna_valor_correta: 'sum','Nº doc.de referência': 'first'}
    df_agrupado = df_cji5.groupby(['Definição do projeto', 'SC_ID_Key']).agg(agg_funcs).reset_index()

    if 'SC ID' not in df_srm.columns:
        st.error("ERRO: A coluna 'SC ID' não foi encontrada no DADOS_SRM!"); return None
    df_srm['SC_ID_Key'] = pd.to_numeric(df_srm['SC ID'], errors='coerce')
    df_srm.dropna(subset=['SC_ID_Key'], inplace=True)
    df_srm['SC_ID_Key'] = df_srm['SC_ID_Key'].astype(int).astype(str)
    df_srm = df_srm.drop_duplicates(subset=['SC_ID_Key'], keep='first')
    
    # ** A LÓGICA OBRIGATÓRIA 'INNER' ESTÁ AQUI **
    df_lancamento_bruto = pd.merge(df_agrupado, df_srm, on='SC_ID_Key', how='inner')
    
    df_lcp.columns = df_lcp.columns.str.strip()
    df_lcp_essencial = df_lcp[['WBS', 'PROJECT NAME']].drop_duplicates(subset=['WBS'])
    df_lancamento_bruto.rename(columns={'Definição do projeto': 'atuação do projeto', 'Valor/moed.transação': 'Valor Total'}, inplace=True)
    df_lancamento_enriquecido = pd.merge(df_lancamento_bruto, df_lcp_essencial, left_on='atuação do projeto', right_on='WBS', how='left')

    chaves_de_agrupamento = ['SC ID', 'atuação do projeto']
    df_agrupado_final = df_lancamento_enriquecido.groupby(chaves_de_agrupamento).agg({'Denominação': lambda x: '\n'.join(x.dropna().astype(str).unique()),'SC Name': 'first', 'Created On': 'first', 'Requester': 'first','Valor Total': 'first', 'Next Approver': 'first', 'Received on': 'first','PROJECT NAME': 'first'}).reset_index()
    
    mapa_colunas = {'SC ID': 'SC', 'atuação do projeto': 'WBS', 'SC Name': 'DESCRIÇÃO','Denominação': 'CONTEÚDO', 'Created On': 'DATA CRIAÇÃO', 'Requester': 'REQUISITANTE','Valor Total': 'VALOR', 'Next Approver': 'PENDENTE COM','Received on': 'RECEBIDA EM', 'PROJECT NAME': 'PROJETO'}
    df_para_atualizar = df_agrupado_final.rename(columns=mapa_colunas)
    
    if not df_para_atualizar.empty:
        df_para_atualizar['SC'] = pd.to_numeric(df_para_atualizar['SC'], errors='coerce').astype('Int64').astype(str)
        df_para_atualizar = df_para_atualizar[df_para_atualizar['SC'] != '<NA>']
    
    progress_bar.progress(25, text="▶️ Etapa 2/4: Carregando planilha de gestão do GitHub...")

    # --- ETAPA 2: Carregar a planilha de gestão do GitHub em um objeto openpyxl ---
    try:
        # Usar BytesIO para ler o arquivo da URL em memória
        response = pd.read_excel(url_gestao, sheet_name=None, engine='openpyxl')
        sheet_name = list(response.keys())[0] # Pega o nome da primeira aba
        
        # Recarregar com openpyxl para manter o objeto do workbook
        workbook = load_workbook(io.BytesIO(pd.read_excel(url_gestao, engine='openpyxl')._data))
        sheet = workbook[sheet_name]
    except Exception as e:
        st.error(f"ERRO ao carregar a planilha de gestão do GitHub: {e}"); return None

    progress_bar.progress(50, text="▶️ Etapa 3/4: Realizando atualização 'cirúrgica'...")

    # --- ETAPA 3: Lógica de atualização célula por célula (preserva cores) ---
    headers = [cell.value for cell in sheet[1]]
    col_map = {name: i+1 for i, name in enumerate(headers)}
    sc_col_num = col_map.get('SC')
    wbs_col_num = col_map.get('WBS')
    if not sc_col_num or not wbs_col_num:
        st.error("As colunas 'SC' e 'WBS' devem existir na planilha de gestão."); return None

    key_row_map = {}
    for i in range(2, sheet.max_row + 1):
        sc_val = str(sheet.cell(row=i, column=sc_col_num).value or '').replace('.0', '').strip()
        wbs_val = str(sheet.cell(row=i, column=wbs_col_num).value or '').strip()
        if sc_val and wbs_val: key_row_map[(sc_val, wbs_val)] = i
    
    novas_linhas_formatar = []
    colunas_gerenciadas_pelo_script = list(mapa_colunas.values())

    for _, row_data in df_para_atualizar.iterrows():
        sc_id = str(row_data.get('SC', ''))
        wbs_id = str(row_data.get('WBS', ''))
        chave_unica = (sc_id, wbs_id)
        
        if chave_unica in key_row_map:
            target_row = key_row_map[chave_unica]
            # Atualiza apenas as colunas que o script gerencia
            for col_name in colunas_gerenciadas_pelo_script:
                if col_name in col_map and col_name in row_data.index:
                    target_col = col_map[col_name]
                    sheet.cell(row=target_row, column=target_col).value = row_data[col_name]
        else:
            # Cria uma nova linha apenas com os dados que o script conhece
            new_row_values = [row_data.get(header_name) for header_name in headers]
            sheet.append(new_row_values)
            novas_linhas_formatar.append(sheet.max_row)

    progress_bar.progress(75, text="▶️ Etapa 4/4: Aplicando formatação profissional...")

    # --- ETAPA 4: Formatação inteligente (só em linhas novas) ---
    header_font = Font(bold=True, color="FFFFFF"); header_fill = PatternFill(start_color="002D62", end_color="002D62", fill_type="solid"); borda_fina = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin')); alinhamento_central_com_quebra = Alignment(horizontal='center', vertical='center', wrap_text=True); alinhamento_central_sem_quebra = Alignment(horizontal='center', vertical='center')
    
    colunas_com_quebra = ['DESCRIÇÃO', 'CONTEÚDO']
    for row_num in novas_linhas_formatar:
        row = sheet[row_num]
        for cell in row:
            cell.border = borda_fina
            header_da_celula = headers[cell.column - 1]
            if header_da_celula in colunas_com_quebra: cell.alignment = alinhamento_central_com_quebra
            else: cell.alignment = alinhamento_central_sem_quebra

    if 'VALOR' in col_map:
        letra_col_valor = chr(ord('A') + col_map['VALOR'] - 1)
        for cell in sheet[letra_col_valor][1:]:
            if isinstance(cell.value, (int, float)): cell.number_format = 'R$ #,##0.00'
            
    # Salva o workbook modificado em memória para download
    output = io.BytesIO()
    workbook.save(output)
    progress_bar.progress(100, text="✅ Processo Concluído!")
    return output.getvalue()


# --- 3. INTERFACE DO APLICATIVO (STREAMLIT) ---
st.title("🤖 Ferramenta de Automação de Lançamentos - FollowUP GY")
st.markdown(f"Esta ferramenta irá ler a planilha de gestão diretamente do [GitHub]({URL_ARQUIVO_GESTAO_RAW}), processar os novos dados que você fornecer e gerar uma versão atualizada para download, **preservando suas cores e comentários**.")
st.markdown("---")

st.header("1. Carregue os 3 arquivos de dados atualizados")
col1, col2, col3 = st.columns(3)
with col1:
    upload_cji5 = st.file_uploader("1. `resultado_cji5.xlsx`", type="xlsx")
with col2:
    upload_srm = st.file_uploader("2. `DADOS_SRM.xlsx`", type="xlsx")
with col3:
    upload_lcp = st.file_uploader("3. `BUSCAR_LCP.xlsx`", type="xlsx")

st.markdown("---")

if upload_cji5 and upload_srm and upload_lcp:
    st.header("2. Execute a automação")
    if st.button("🚀 Processar Arquivos e Gerar Relatório Final"):
        
        dados_excel_final = executar_atualizacao_cirurgica(upload_cji5, upload_srm, upload_lcp, URL_ARQUIVO_GESTAO_RAW)
        
        if dados_excel_final:
            st.header("3. Download do Relatório Atualizado")
            st.download_button(
                label="📥 Baixar Planilha Final Formatada",
                data=dados_excel_final,
                file_name="Gestão_de_SC_em_aberto_ATUALIZADA.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.balloons()
else:
    st.info("Aguardando o carregamento dos 3 arquivos para habilitar o processamento.")