import streamlit as st
import pandas as pd
import io
from openpyxl.styles import Border, Side, Alignment, Font, PatternFill

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="FollowUP-GY Automação",
    page_icon="🤖",
    layout="wide"
)

# --- NOMES DOS ARQUIVOS MESTRE (LIDOS DO GITHUB) ---
ARQUIVO_GESTAO = "Gestão de SC em aberto - Engenharia de Projetos.xlsx"

# --- 2. FUNÇÕES COM A LÓGICA DO SEU PROJETO ---

def processar_dados_iniciais(arquivo_cji5, arquivo_srm, arquivo_lcp):
    """
    Esta função une a lógica do Planilhas.py com a parte de 
    enriquecimento do LançamentoFIM.py.
    """
    st.write("▶️ **Etapa 1/3:** Consolidando e enriquecendo dados...")
    try:
        df_cji5 = pd.read_excel(arquivo_cji5)
        df_srm = pd.read_excel(arquivo_srm)
        df_lcp = pd.read_excel(arquivo_lcp, sheet_name='Capex', header=3, dtype={'WBS': str})
    except Exception as e:
        st.error(f"ERRO ao ler os arquivos de upload: {e}"); return None

    # --- Lógica de 'Planilhas.py' ---
    df_cji5['Nº doc.de referência'] = df_cji5['Nº doc.de referência'].astype(str)
    df_cji5 = df_cji5[df_cji5['Nº doc.de referência'].str.startswith('S', na=False)].copy()
    if df_cji5.empty:
        st.warning("Nenhuma SC encontrada na planilha Cji5."); return pd.DataFrame()

    df_cji5['SC_ID_Key'] = df_cji5['Nº doc.de referência'].str.replace('S', '', n=1, regex=False).str.strip()
    df_cji5['SC_ID_Key'] = pd.to_numeric(df_cji5['SC_ID_Key'], errors='coerce')
    df_cji5.dropna(subset=['SC_ID_Key'], inplace=True)
    df_cji5['SC_ID_Key'] = df_cji5['SC_ID_Key'].astype(int).astype(str)
    
    coluna_valor_correta = 'Valor/moed.transação'
    if coluna_valor_correta not in df_cji5.columns:
        st.error(f"ERRO: A coluna '{coluna_valor_correta}' não foi encontrada no arquivo Cji5. Verifique o arquivo de entrada.")
        return None
    df_cji5[coluna_valor_correta] = pd.to_numeric(df_cji5[coluna_valor_correta], errors='coerce').fillna(0)
    
    agg_funcs = {'Material': lambda x: ';\n'.join(x.dropna().astype(str).unique()),'Denominação': lambda x: ';\n'.join(x.dropna().astype(str).unique()),'Quantidade total': lambda x: ';\n'.join(x.dropna().astype(str)),coluna_valor_correta: 'sum','Nº doc.de referência': 'first'}
    df_agrupado = df_cji5.groupby(['Definição do projeto', 'SC_ID_Key']).agg(agg_funcs).reset_index()

    if 'SC ID' not in df_srm.columns:
        st.error("ERRO CRÍTICO: A coluna 'SC ID' não foi encontrada no arquivo DADOS_SRM.xlsx!"); return None
    df_srm['SC_ID_Key'] = pd.to_numeric(df_srm['SC ID'], errors='coerce')
    df_srm.dropna(subset=['SC_ID_Key'], inplace=True)
    df_srm['SC_ID_Key'] = df_srm['SC_ID_Key'].astype(int).astype(str)
    df_srm = df_srm.drop_duplicates(subset=['SC_ID_Key'], keep='first')
    
    df_lancamento_bruto = pd.merge(df_agrupado, df_srm, on='SC_ID_Key', how='inner')
    
    # --- Lógica de enriquecimento (do LançamentoFIM.py) ---
    df_lcp.columns = df_lcp.columns.str.strip()
    df_lcp_essencial = df_lcp[['WBS', 'PROJECT NAME']].drop_duplicates(subset=['WBS'])
    
    # Renomeia as colunas para o merge e para o próximo passo
    if 'Definição do projeto' in df_lancamento_bruto.columns:
        df_lancamento_bruto.rename(columns={'Definição do projeto': 'atuação do projeto', 'Valor/moed.transação': 'Valor Total'}, inplace=True)
    
    df_lancamento_enriquecido = pd.merge(df_lancamento_bruto, df_lcp_essencial, left_on='atuação do projeto', right_on='WBS', how='left')

    st.success("✅ Concluído: Dados consolidados e enriquecidos.")
    return df_lancamento_enriquecido


def atualizar_gestao_final(df_lancamento_enriquecido, df_gestao_antiga):
    """Lógica de atualização 'cirúrgica' do LançamentoFIM.py."""
    st.write("▶️ **Etapa 2/3:** Atualizando a planilha principal de gestão...")
    
    chaves_de_agrupamento = ['SC ID', 'atuação do projeto']
    df_agrupado = df_lancamento_enriquecido.groupby(chaves_de_agrupamento).agg({'Denominação': lambda x: '\n'.join(x.dropna().astype(str).unique()),'SC Name': 'first', 'Created On': 'first', 'Requester': 'first','Valor Total': 'first', 'Next Approver': 'first', 'Received on': 'first','PROJECT NAME': 'first'}).reset_index()
    mapa_colunas = {'SC ID': 'SC', 'atuação do projeto': 'WBS', 'SC Name': 'DESCRIÇÃO','Denominação': 'CONTEÚDO', 'Created On': 'DATA CRIAÇÃO', 'Requester': 'REQUISITANTE','Valor Total': 'VALOR', 'Next Approver': 'PENDENTE COM','Received on': 'RECEBIDA EM', 'PROJECT NAME': 'PROJETO'}
    df_para_atualizar = df_agrupado.rename(columns=mapa_colunas)
    
    df_para_atualizar['SC'] = pd.to_numeric(df_para_atualizar['SC'], errors='coerce').astype('Int64').astype(str)
    df_para_atualizar = df_para_atualizar[df_para_atualizar['SC'] != '<NA>']
    if 'WBS' in df_para_atualizar.columns: df_para_atualizar['WBS'] = df_para_atualizar['WBS'].str.strip()
    
    df_gestao_antiga['SC'] = df_gestao_antiga['SC'].astype(str).str.replace('.0', '', regex=False).str.strip()
    if 'WBS' in df_gestao_antiga.columns: df_gestao_antiga['WBS'] = df_gestao_antiga['WBS'].astype(str).str.strip()
    
    df_para_atualizar.set_index(['SC', 'WBS'], inplace=True)
    df_gestao_antiga.set_index(['SC', 'WBS'], inplace=True)
    
    df_gestao_antiga.update(df_para_atualizar)
    
    novas_linhas = df_para_atualizar[~df_para_atualizar.index.isin(df_gestao_antiga.index)]
    df_gestao_final = pd.concat([df_gestao_antiga, novas_linhas])
    df_gestao_final.reset_index(inplace=True)

    st.success("✅ Concluído: Planilha de gestão atualizada.")
    return df_gestao_final


def formatar_excel_para_download(df):
    """Aplica a formatação 'Goodyear' na planilha final."""
    st.write("▶️ **Etapa 3/3:** Aplicando formatação profissional...")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='FollowUP_SCs')
        workbook  = writer.book; worksheet = writer.sheets['FollowUP_SCs']
        header_font = Font(bold=True, color="FFFFFF"); header_fill = PatternFill(start_color="002D62", end_color="002D62", fill_type="solid"); borda_fina = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin')); alinhamento_central_com_quebra = Alignment(horizontal='center', vertical='center', wrap_text=True); alinhamento_central_sem_quebra = Alignment(horizontal='center', vertical='center')
        worksheet.row_dimensions[1].height = 25
        headers = [cell.value for cell in worksheet[1]]
        for cell in worksheet[1]: cell.font = header_font; cell.fill = header_fill; cell.border = borda_fina; cell.alignment = alinhamento_central_sem_quebra
        colunas_com_quebra = ['DESCRIÇÃO', 'CONTEÚDO']
        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
            for cell in row:
                cell.border = borda_fina; header_da_celula = headers[cell.column - 1]
                if header_da_celula in colunas_com_quebra: cell.alignment = alinhamento_central_com_quebra
                else: cell.alignment = alinhamento_central_sem_quebra
        larguras = {'SC': 15, 'WBS': 25, 'PROJETO': 45, 'DESCRIÇÃO': 45, 'CONTEÚDO': 50, 'VALOR': 18, 'DATA CRIAÇÃO': 18, 'REQUISITANTE': 25, 'RECEBIDA EM': 18, 'PENDENTE COM': 25, 'STATUS': 15, 'OK': 10, 'COMENTARIO': 50, 'Complemento dos materiais': 50}
        for i, header in enumerate(headers):
            letra_col = chr(ord('A') + i)
            if header in larguras: worksheet.column_dimensions[letra_col].width = larguras[header]
            if header == 'VALOR':
                for cell in worksheet[letra_col][1:]:
                    if isinstance(cell.value, (int, float)): cell.number_format = 'R$ #,##0.00'
    st.success("✅ Concluído: Formatação aplicada.")
    return output.getvalue()


# --- 3. INTERFACE DO APLICATIVO ---
st.title("🤖 Ferramenta de Automação de Lançamentos - FollowUP GY")
st.info(f"**Arquivo Mestre em uso:** `{ARQUIVO_GESTAO}`")
st.markdown("---")
st.header("1. Carregue os arquivos de dados")

# Pedimos os 3 arquivos para o usuário
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
        with st.spinner("Aguarde... A mágica está acontecendo."):
            try:
                # Carregamos o arquivo mestre do GitHub aqui
                df_gestao_mestre = pd.read_excel(ARQUIVO_GESTAO)

                # Etapa 1: Chama a primeira função com os 3 uploads
                df_intermediario = processar_dados_iniciais(upload_cji5, upload_srm, upload_lcp)
                
                if df_intermediario is not None and not df_intermediario.empty:
                    # Etapa 2: Chama a segunda função apenas com o resultado da primeira e o mestre
                    df_final = atualizar_gestao_final(df_intermediario, df_gestao_mestre)

                    if df_final is not None:
                        # Etapa 3: Formatação
                        dados_excel_formatado = formatar_excel_para_download(df_final)
                        st.header("3. Download do Relatório Atualizado")
                        st.download_button(
                            label="📥 Baixar Planilha Final Formatada",
                            data=dados_excel_formatado,
                            file_name="Gestão_de_SC_em_aberto_ATUALIZADA.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        st.balloons()
            except FileNotFoundError:
                st.error(f"ERRO: O arquivo mestre '{ARQUIVO_GESTAO}' não foi encontrado no repositório. Verifique se ele foi enviado ao GitHub.")
            except Exception as e:
                st.error(f"Ocorreu um erro inesperado durante o processamento: {e}")
else:
    st.info("Por favor, carregue os 3 arquivos necessários para habilitar o botão de processamento.")
