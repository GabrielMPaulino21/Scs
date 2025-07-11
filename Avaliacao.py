import streamlit as st
import pandas as pd
import os
import plotly.express as px
from PIL import Image
import base64
import time
import openpyxl

# --- FUNÇÃO PARA CODIFICAR IMAGEM (PARA O PLANO DE FUNDO) ---
@st.cache_data
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

def set_png_as_page_bg(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    if bin_str is None:
        st.error(f"Arquivo de imagem de fundo não encontrado em '{png_file}'. Verifique a pasta 'assets'.")
        return
        
    page_bg_img = f'''
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: scroll;
    }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)


# --- CONFIGURAÇÕES DA PÁGINA ---
try:
    page_icon = Image.open("assets/logo_sidebar.png")
except FileNotFoundError:
    page_icon = "📊"

st.set_page_config(
    page_title="AVALIAÇÃO DE FORNECEDORES",
    page_icon=page_icon,
    layout="wide"
)

# --- DADOS E CONSTANTES ---
ARQUIVO_VOTOS = 'votos.csv'
# Caminho relativo para o arquivo Excel com a lista de projetos.
# O arquivo BUSCAR_LCP.xlsx deve estar na mesma pasta que este script.
ARQUIVO_PROJETOS = "BUSCAR_LCP.xlsx" 

ADMIN_KEYS = [('gabriel', 'paulino'), ('rodrigo', 'saito')]
EMPRESAS = [
    "ABSAFE ENGENHARIA E SEGURANCA", "ASSESSORIA TECNICA ATENE LTDA", "ATUS ENGENHARIA LDA", "BECOMEX CONSULTORIA LTDA",
    "BONA - TERCEIRIZACAO DE MAO-DE-OBRA PARA LOGISTICA LTDA", "CASTELL COMERCIAL DE EQUIPAMENTOS", "CAVE ENGENHARIA E OBRAS LTDA",
    "CHARLES ELBLINK ME", "CLIMAVENT COMERCIO", "CONDUTIVA ENGENHARIA ELETRICA LTDA", "COPE E CIA LTDA",
    "ENGECOMP MANUTENCAO INDUSTRIAL LTDA", "ESTRUTEZZA INDUSTRIA E COMERCIO LTDA", "FRM ENGENHARIA LTDA",
    "GIISAPTEC SOLUCOES INDUSTRIAIS LTDA", "JOSE FERNANDO ALVES JUNIOR EPP", "LOCALLTAINER LOCACOES DE CONTAINERS LTDA.",
    "M GARCIA SERRALHERIA E CALDEIRARIA LTDA", "MAMUTH TRANSPORTE DE MAQUINAS LTDA", "MANTEST ENGENHARIA ELETRICA LTDA",
    "MARCATO GESTAO EMPRESARIAL E TERCEIRIZACAO DE SERVICOS EIRELLI", "MENSURA ENGENHARIA LTDA", "MP ENGENHARIA ELETRICA LTDA.",
    "NOVAC CONSTRUCOES EMPREENDIMENTOS LTDA", "ODOURNET BRASIL LTDA.", "PEOPLE TEAM LTDA",
    "PROENG MONTAGENS E MANUTENCAO INDUSTRIAL LTDA", "RICAMIL ENGENHARIA E SERVICOS LTDA", "RIDARP CONSTRUCOES LTDA",
    "ROCKWELL AUTOMATION DO BRASIL LTDA", "RYCE ENGENHARIA & CONSTRUCAO LTDA.",
    "SGS INDUSTRIAL - INSTALACOES, TESTES E COMISSIONAMENTOS LTDA", "SICK SOLUCAO EM SENSORES LTDA",
    "SIEMENS INFRAESTRUTURA E INDUSTRIA LTDA", "SOS SERVICE COMERCIO E ENGENHARIA LTDA", "SPI INTEGRACAO DE SISTEMAS LTDA",
    "TEC AND TEC LATAM AMERICA LTDA", "TITAN INDUSTRIA E COMERCIO DE FERRAMENTAS E PERIFERICOS LTDA",
    "TOPICO LOCACOES DE GALPOES E EQUIPAMENTOS PARA INDUSTRIAS S.A", "VENDART SOLUCOES INDUSTRIAIS LTDA",
    "VENDOR TRADUCOES TECNICAS E COMERCIO LTDA", "VIVA EQUIPAMENTOS INDUSTRIAIS E COMERCIO LTDA",
    "WORK'S ENGENHARIA E MONTAGENS INDUSTRIAIS LTDA"
]
PERGUNTAS = {
    "SAFETY": { "1.1": "Accidents / near miss", "1.2": "Work Permit (LTR, PPT) performance", "1.3": "EHS documentation (like training certifications and clinic exams (ASO).", "1.4": "Leadership - Safety technician is on work execution", "1.5": "Safety audit" },
    "QUALITY": { "2.1": "Delivering jobs on time", "2.2": "Executions comply with designs", "2.3": "Housekeeping during work execution and after", "2.4": "Work tools condition (personal and equipments)", "2.5": "Delivery jobs on cost" },
    "PEOPLE": { "3.1": "Crew sizing according to approved contracts", "3.2": "Workteam knowledge meet the minimum technical requirements", "3.3": "Leadership - Supervisors is on work execution" },
    "DOCUMENTATION": { "4.1": "Supplier is following accordinly with SAM system requirements (evidences like schedules, measurements, pictures, reports, ART)", "4.2": "Suppliers delivery all the documentation (Company and employees) on time, according to the plan.", "4.3": "Suppliers deliver all the project documentation required (Ex: As Built, Drawings, Data sheets, Manuals, etc)." }
}
OPCOES_VOTO = ['1', '2', '3', '4', '5', 'N/A']

RUBRICA = {
    "SAFETY": {
        "1.1": ["1 OSHA Accident", "1 Serious Accident and 0 OSHA Accident", "0 Accident and 2 or more near miss", "0 Accident and 1 near miss", "0 near miss / accidents"],
        "1.2": ["rarely shows commitment with LTR and PPTs, needs constants improvements and guidances", "sometimes shows commitment with LTR and PPTs, but still needs improvements and guidances.", "shows commitment with LTR and PPTs, requiring punctual orientations.", "Often shows commitment with LTR and PPTs, sharing best practices and process improvements to contributes with safety.", "shows fully commitment with LTR and PPTs, being a partner to the safety and a benchmarking for other companies."],
        "1.3": ["rarely delivery to the EHS on time, needs constants improvements and guidances", "sometimes delivery to the EHS on time, but still needs improvements and guidances.", "delivery to the EHS on time, requiring punctual orientations.", "Often delivery to the EHS on time, sharing best practices and process improvements to contributes with safety.", "shows fully commitment to delivery on time, being a partner to the safety and a benchmarking for other companies."],
        "1.4": ["rarely leadership is present on the job", "sometimes leadership is present on the job, but still needs improvements and guidances.", "leadership is present on the job, requiring punctual orientations.", "Often leadership is present on the job, providing technical support and safety conditions to their associates.", "shows fully commitment to provide leadership full time by service, being a benchmarking for other companies."],
        "1.5": ["rarely shows commitment with objectives and procedures, needs constants improvements and guidances", "sometimes shows commitment with objectives and procedures, but still needs improvements and guidances.", "shows commitment with objectives and procedures, requiring punctual orientations.", "Often shows commitment with objectives and procedures, sharing best practices and process improvements to contributes with business success.", "shows fully commitment with objectives and procedures, being a partner to the business and a benchmarking for other companies."]
    },
    "QUALITY": {
        "2.1": ["rarely shows commitment to delivery on time, needs constants improvements and guidances", "sometimes shows commitment to delivery on time, but still needs improvements and guidances.", "shows commitment to delivery on time, requiring punctual orientations.", "Often shows commitment to delivery on time, applying proactive actions to mitigate delays.", "shows fully commitment to delivery on time, being a partner to the business and a benchmarking for other companies."],
        "2.2": ["rarely shows commitment to execute services according to design, needs constants improvements and guidances", "sometimes shows commitment to execute services according to design, but still needs improvements and guidances.", "shows commitment to execute services according to design, requiring punctual orientations.", "Often shows commitment to execute services according to design, avoiding reworks.", "shows fully commitment to execute services according to design, avoiding reworks and being a benchmarking for other companies."],
        "2.3": ["rarely shows commitment with housekeeping, needs constants improvements and guidances", "sometimes shows commitment with housekeeping, but still needs improvements and guidances.", "shows commitment with housekeeping, requiring punctual orientations.", "Often shows commitment with housekeeping, sharing best practices to contributes with safety.", "shows fully commitment with housekeeping, being a partner to the safety and a benchmarking for other companies."],
        "2.4": ["rarely shows commitment to provide tools and personal protection according to standards, needs constants improvements and guidances", "sometimes shows commitment to provide tools and personal protection according to standards, but still needs improvements and guidances.", "shows commitment to provide tools and personal protection according to standards, requiring punctual orientations.", "Often shows commitment to provide tools and personal protection according to standards, providing safety conditions to their associates.", "shows fully commitment to provide tools and personal protection according to standards, providing safety conditions to their associates and being a benchmarking for other companies."],
        "2.5": ["Overcost > 21%", "15% < Overcost < 20%", "10% < Overcost < 0%", "0%", "Deliver the project with saving"]
    },
    "PEOPLE": {
        "3.1": ["rarely shows commitment to provide resources according to service complexity, needs constants improvements and guidances", "sometimes shows commitment to provide resources according to service complexity, but still needs improvements and guidances.", "shows commitment to provide resources according to service complexity, requiring punctual orientations.", "Often shows commitment to provide resources according to service complexity, with flexibility to mobilize resources quickly in order to avoid any impacts for the business.", "shows fully commitment with objectives and procedures, providing resources according to service complexity, with flexibility to mobilize resources quickly in order to avoid any impacts for the business, being a partner to the business and a benchmarking for other companies."],
        "3.2": ["Full team (leadership and operational) shows low level of qualification, needs replacement.", "operational team are fully dependent of leadership to execute the service, needs improvements.", "shows commitment to provide resources according to service complexity, requiring punctual orientations.", "Often shows commitment to provide resources according to service complexity and requested qualification, presenting plans of development in order to avoid any impacts for the business.", "shows fully commitment with objectives and procedures, providing resources according to service complexity and high qualification of resources required."],
        "3.3": ["rarely leadership is present on the job", "sometimes leadership is present on the job, but still needs improvements and guidances.", "leadership is present on the job, requiring punctual orientations.", "Often leadership is present on the job, providing technical support and safety conditions to their associates.", "shows fully commitment to provide leadership full time by service, being a benchmarking for other companies."]
    },
    "DOCUMENTATION": {
        "4.1": ["rarely shows commitment to provide adequate evidences, needs constants improvements and guidances", "sometimes shows commitment to provide adequate evidences, but still needs improvements and guidances.", "shows commitment to provide to provide adequate evidences, requiring punctual orientations.", "Often shows commitment to provide adequate evidences, sharing best practices and process improvements to contributes with business success.", "shows fully commitment to provide adequate evidences, being a partner to the business and a benchmarking for other companies."],
        "4.2": ["More than 30 days of delay comparing to the plan, to deliver all the documentation", "More than 15 days of delay comparing to the plan, to deliver all the documentation", "Maximum of 5 days of delay comparing to the plan, to deliver all the documentation", "Deliver all the documentation on time, comparing to the plan.", "Deliver all the documentation anticipated"],
        "4.3": ["do not deliver the project documentation according to the contract / scope of work.", "missing no critical project documentation", "deliver all the project documentation according to the contract / scope of work", "deliver more project documentation than requested", "exceed the deliver expectatives"]
    }
}


# --- FUNÇÕES DE DADOS ---
def carregar_votos():
    if os.path.exists(ARQUIVO_VOTOS):
        return pd.read_csv(ARQUIVO_VOTOS, dtype={'projeto': str})
    else:
        return pd.DataFrame(columns=['user_name', 'projeto', 'empresa', 'categoria', 'pergunta_id', 'pergunta_texto', 'voto'])

@st.cache_data
def carregar_projetos(caminho_arquivo):
    """Lê as abas do arquivo Excel, concatena as colunas e retorna uma lista única de projetos LCP."""
    try:
        df_capex = pd.read_excel(caminho_arquivo, sheet_name="Capex", header=3)
        df_ame = pd.read_excel(caminho_arquivo, sheet_name="AME - Quarterly", header=3)

        projetos_capex = []
        if 'WBS' in df_capex.columns and 'PROJECT NAME' in df_capex.columns:
            df_capex.dropna(subset=['WBS', 'PROJECT NAME'], inplace=True)
            projetos_capex = (df_capex['WBS'].astype(str) + " - " + df_capex['PROJECT NAME'].astype(str)).tolist()

        projetos_ame = []
        if 'WBS' in df_ame.columns and 'PROJECT NAME' in df_ame.columns:
            df_ame.dropna(subset=['WBS', 'PROJECT NAME'], inplace=True)
            projetos_ame = (df_ame['WBS'].astype(str) + " - " + df_ame['PROJECT NAME'].astype(str)).tolist()

        todos_projetos = projetos_capex + projetos_ame

        # Filtra a lista para manter apenas os projetos que começam com "LCP"
        projetos_lcp = [proj for proj in todos_projetos if proj.strip().startswith("LCP")]

        # Remove duplicatas e ordena a lista final
        projetos_finais = sorted(list(set(projetos_lcp)))
        
        return projetos_finais

    except FileNotFoundError:
        st.error(f"ERRO: O arquivo de projetos não foi encontrado em '{caminho_arquivo}'. Verifique se ele está na mesma pasta do script.")
        return ["ERRO: Arquivo de projetos não encontrado"]
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo de projetos: {e}")
        return [f"ERRO: {e}"]

# --- GERENCIAMENTO DE ESTADO ---
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
    st.session_state.is_admin = False

# --- LÓGICA DE EXIBIÇÃO ---

if not st.session_state.user_name:
    set_png_as_page_bg('assets/login_fundo.jpg')
    st.markdown("""<style> h1, label { color: black !important; background-color: rgba(255, 255, 255, 0.7); padding: 10px; border-radius: 10px; font-weight: bold !important; } </style>""", unsafe_allow_html=True)
    st.title("Bem-vindo ao Sistema de Avaliação de Fornecedores")
    with st.form("login_form"):
        nome = st.text_input("Digite seu nome completo:", key="login_name")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            if nome:
                st.session_state.user_name = nome.strip().upper()
                nome_digitado_lower = st.session_state.user_name.lower()
                st.session_state.is_admin = any(all(key in nome_digitado_lower for key in key_tuple) for key_tuple in ADMIN_KEYS)
                st.rerun() 
            else:
                st.error("Por favor, insira seu nome para continuar.")

else:
    # Carrega a lista de projetos LCP do arquivo Excel
    lista_projetos_lcp = carregar_projetos(ARQUIVO_PROJETOS)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("RELATÓRIO DE AVALIAÇÃO DE FORNECEDORES")
    with col2:
        if os.path.exists("assets/banner_votacao.jpg"):
            st.image("assets/banner_votacao.jpg", width=250) 
            
    st.sidebar.image("assets/logo_sidebar.png")
    st.sidebar.success(f"Logado como:\n**{st.session_state.user_name}**")
    if st.session_state.is_admin:
        st.sidebar.warning("👑 **Nível de Acesso:** Administrador")
    if st.sidebar.button("Sair (Logout)"):
        st.session_state.user_name = None
        st.session_state.is_admin = False
        st.rerun()

    tab_votacao, tab_projetos, tab_relatorio, tab_dados, tab_criterios = st.tabs([
        "📝 NOVA AVALIAÇÃO", 
        "📂 PROJETOS AVALIADOS",
        "📊 RELATÓRIO DE MÉDIAS", 
        "⚙️ DADOS E ADMINISTRAÇÃO",
        "📘 CRITÉRIOS DE AVALIAÇÃO"
    ])
    df_votos_geral = carregar_votos()
    
    with tab_votacao:
        st.header("Registrar Nova Avaliação de Projeto")
        st.info("Selecione o projeto, o fornecedor e responda às perguntas para registrar uma nova avaliação.")
        with st.form(key="form_nova_avaliacao", clear_on_submit=True):
            
            projeto = st.selectbox(
                "Projeto*", 
                options=lista_projetos_lcp,
                index=None,
                placeholder="Selecione um projeto LCP da lista..."
            )
            
            empresa_selecionada = st.selectbox("Fornecedor*", options=EMPRESAS, index=None, placeholder="Escolha uma empresa...")
            st.markdown("---")
            respostas = {}
            if projeto and empresa_selecionada:
                st.subheader(f"Avaliação para: {empresa_selecionada} (Projeto: {projeto})")
                for categoria, perguntas_categoria in PERGUNTAS.items():
                    st.markdown(f"#### {categoria}")
                    for pid, ptexto in perguntas_categoria.items():
                        respostas[f"{categoria}_{pid}"] = st.radio(f"**{pid}** - {ptexto}", OPCOES_VOTO, horizontal=True, key=f"vote_{projeto}_{empresa_selecionada}_{pid}")
            
            submitted = st.form_submit_button("Registrar Avaliação")
            if submitted:
                if not projeto or not empresa_selecionada:
                    st.error("Por favor, selecione um Projeto e um Fornecedor.")
                else:
                    ja_votou = not df_votos_geral[(df_votos_geral['user_name'] == st.session_state.user_name) & (df_votos_geral['empresa'] == empresa_selecionada) & (df_votos_geral['projeto'] == projeto)].empty
                    if ja_votou:
                        st.error(f"Você já avaliou a empresa '{empresa_selecionada}' para o projeto '{projeto}'.")
                    else:
                        novos_votos = [{'user_name': st.session_state.user_name, 'projeto': projeto, 'empresa': empresa_selecionada, 'categoria': c.split('_')[0], 'pergunta_id': c.split('_')[1], 'pergunta_texto': PERGUNTAS[c.split('_')[0]][c.split('_')[1]], 'voto': v} for c, v in respostas.items()]
                        df_novos_votos = pd.DataFrame(novos_votos)
                        df_votos_atualizado = pd.concat([df_votos_geral, df_novos_votos], ignore_index=True)
                        df_votos_atualizado.to_csv(ARQUIVO_VOTOS, index=False)
                        st.success(f"Avaliação para o projeto '{projeto}' registrada com sucesso!")

    with tab_projetos:
        st.header("Visão Geral de Projetos Avaliados")
        if df_votos_geral.empty:
            st.info("Nenhuma avaliação de projeto foi registrada ainda.")
        else:
            projetos_avaliados = df_votos_geral.groupby('projeto')['empresa'].unique()
            for nome_projeto, empresas_no_projeto in projetos_avaliados.items():
                with st.expander(f"**Projeto:** {nome_projeto} ({len(empresas_no_projeto)} empresa(s) avaliada(s))"):
                    for emp in sorted(empresas_no_projeto):
                        st.markdown(f"- {emp}")

    with tab_relatorio:
        st.header("Análise de Desempenho dos Fornecedores")
        if df_votos_geral.empty:
            st.info("Ainda não há votos registrados.")
        else:
            lista_projetos_filtro = ["Todos os Projetos"] + sorted(df_votos_geral['projeto'].unique().tolist())
            projeto_filtrado = st.selectbox("Filtrar por Projeto:", lista_projetos_filtro)
            
            df_filtrado = df_votos_geral if projeto_filtrado == "Todos os Projetos" else df_votos_geral[df_votos_geral['projeto'] == projeto_filtrado]
            df_calculo = df_filtrado[df_filtrado['voto'] != 'N/A'].copy()
            df_calculo['voto'] = pd.to_numeric(df_calculo['voto'])
            media_por_categoria = df_calculo.groupby(['empresa', 'categoria'])['voto'].mean().reset_index()
            media_por_categoria.rename(columns={'voto': 'media_avaliacao'}, inplace=True)
            st.subheader("Gráficos Individuais por Fornecedor")
            empresas_avaliadas = media_por_categoria['empresa'].unique()
            if not empresas_avaliadas.any():
                st.warning(f"Nenhuma avaliação encontrada para o projeto '{projeto_filtrado}'.")
            else:
                cols = st.columns(3)
                for i, empresa in enumerate(empresas_avaliadas):
                    df_empresa = media_por_categoria[media_por_categoria['empresa'] == empresa]
                    fig = px.bar(df_empresa, x='categoria', y='media_avaliacao', color='categoria', title=empresa, text_auto='.2f')
                    fig.update_layout(yaxis_range=[0, 5], xaxis_title=None, yaxis_title="Média", showlegend=False, title_font_size=14, title_x=0.5)
                    with cols[i % 3]:
                        st.plotly_chart(fig, use_container_width=True)
                st.markdown("---")
                st.subheader("Tabela Geral de Médias")
                tabela_pivot = media_por_categoria.pivot_table(index='empresa', columns='categoria', values='media_avaliacao').round(2)
                st.dataframe(tabela_pivot, use_container_width=True)

    with tab_dados:
        st.header("Painel de Administração e Dados")
        if not st.session_state.is_admin:
            st.warning("🔒 Acesso Restrito. Apenas administradores podem visualizar esta aba.")
            st.stop()
        st.subheader("Resumo de Participação por Usuário")
        if df_votos_geral.empty:
            st.info("Nenhuma participação registrada ainda.")
        else:
            for user_name, user_df in df_votos_geral.groupby('user_name'):
                with st.expander(f"**Usuário:** {user_name}"):
                    projetos_do_usuario = user_df.groupby('projeto')['empresa'].unique()
                    for proj, emps in projetos_do_usuario.items():
                        st.markdown(f"   - **Projeto:** {proj} | **Empresas:** {', '.join(sorted(emps))}")
        st.markdown("---")
        st.subheader("Administração de Avaliações")
        if not df_votos_geral.empty:
            usuarios_com_voto = sorted(df_votos_geral['user_name'].unique())
            user_selecionado_admin = st.selectbox("1. Selecione o usuário:", usuarios_com_voto, index=None)
            if user_selecionado_admin:
                avaliacoes_do_usuario = df_votos_geral[df_votos_geral['user_name'] == user_selecionado_admin][['projeto', 'empresa']].drop_duplicates().to_records(index=False)
                avaliacao_para_apagar = st.selectbox("2. Selecione a avaliação para apagar:", [f"Projeto: {p} | Empresa: {e}" for p, e in avaliacoes_do_usuario], index=None)
                if avaliacao_para_apagar:
                    projeto_apagar = avaliacao_para_apagar.split(' | ')[0].replace('Projeto: ', '')
                    empresa_apagar = avaliacao_para_apagar.split(' | ')[1].replace('Empresa: ', '')
                    st.warning(f"Você está prestes a apagar a avaliação do projeto '{projeto_apagar}' para a empresa '{empresa_apagar}'.")
                    if st.button("Confirmar Exclusão da Avaliação", type="primary"):
                        df_final = df_votos_geral[~((df_votos_geral['user_name'] == user_selecionado_admin) & (df_votos_geral['projeto'] == projeto_apagar) & (df_votos_geral['empresa'] == empresa_apagar))]
                        df_final.to_csv(ARQUIVO_VOTOS, index=False)
                        st.success("Avaliação apagada com sucesso.")
                        st.rerun()
        st.markdown("---")
        st.subheader("Visualizar Todos os Votos Registrados")
        st.dataframe(df_votos_geral, use_container_width=True)
        st.markdown("---")
        st.subheader("Zona de Perigo: Apagar Todo o Histórico")
        st.warning("🚨 CUIDADO: Esta ação apagará **TODAS AS AVALIAÇÕES** permanentemente.")
        if st.checkbox("Eu entendo e quero apagar todos os dados."):
            if st.button("APAGAR TUDO", type="primary"):
                if os.path.exists(ARQUIVO_VOTOS):
                    os.remove(ARQUIVO_VOTOS)
                    st.success("Todo o histórico de votos foi apagado.")
                    st.rerun()

    with tab_criterios:
        st.header("📘 Guia de Critérios para Avaliação")
        st.info("Use esta guia para consultar o que cada nota significa para cada pergunta específica.")
        legenda_geral = {"Nota": ["1", "2", "3", "4", "5"], "Significado": ["Needs improvement", "Meets partially the expectations", "Meets the expectations", "Exceed partially the expectations", "Exceed the expectations"]}
        st.table(pd.DataFrame(legenda_geral).set_index('Nota'))
        st.markdown("---")
        for categoria, perguntas in PERGUNTAS.items():
            with st.expander(f"Critérios para a Categoria: **{categoria}**"):
                for pid, ptexto in perguntas.items():
                    st.markdown(f"##### Pergunta {pid}: {ptexto}")
                    if categoria in RUBRICA and pid in RUBRICA[categoria]:
                        st.table(pd.DataFrame({'Nota': [1, 2, 3, 4, 5], 'Descrição do Critério': RUBRICA[categoria][pid]}).set_index('Nota'))
                    else:
                        st.warning("Critérios para esta pergunta não definidos.")