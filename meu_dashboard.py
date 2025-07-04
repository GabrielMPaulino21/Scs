import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np

# --- Configuração da Página do Dashboard ---
st.set_page_config(layout="wide", page_title="Dashboard de Urgência de SCs")

# --- Carregamento de Dados e Cálculos Essenciais ---
@st.cache_data
def carregar_dados_do_resumo():
    try:
        arquivo_resumo = "Gestão de SC em aberto - Engenharia de Projetos.xlsx"
        df = pd.read_excel(arquivo_resumo, header=0)
        data_modificacao = datetime.now()
    except FileNotFoundError:
        st.error(f"ERRO CRÍTICO: Arquivo de resumo '{arquivo_resumo}' não foi encontrado no repositório do GitHub.")
        return pd.DataFrame(), None
    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo de resumo: {e}")
        return pd.DataFrame(), None

    # --- Limpeza e Preparação dos Dados ---
    
    # *** CORREÇÃO FINALÍSSIMA APLICADA AQUI ***
    # Agora, a única condição para uma linha ser apagada é se a coluna 'SC' estiver vazia.
    df.dropna(subset=['SC'], inplace=True)
            
    df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce').fillna(0)
    df['DATA CRIAÇÃO'] = pd.to_datetime(df['DATA CRIAÇÃO'], errors='coerce')
    df['SC'] = df['SC'].astype(str).str.strip()
    
    # Preenche outras colunas importantes com um placeholder para evitar erros
    df['WBS'] = df['WBS'].fillna('Não atribuído').astype(str).str.strip()
    df['REQUISITANTE'] = df['REQUISITANTE'].fillna('Não informado').astype(str)
    df['PENDENTE COM'] = df['PENDENTE COM'].fillna('Não informado').astype(str)
    df['PROJETO'] = df['PROJETO'].fillna('Não informado').astype(str)
    
    # Filtro final para remover qualquer resquício de linhas vazias
    df = df[df['SC'] != '']
    df = df[df['SC'].str.lower() != 'nan']

    # Recalcula as colunas após a limpeza
    df.dropna(subset=['DATA CRIAÇÃO'], inplace=True)
    df['SC_WBS'] = df['SC'] + '-' + df['WBS']
    df['PROJETO_COMPLETO'] = df['PROJETO'] + " (" + df['WBS'] + ")"
    hoje = pd.to_datetime(datetime.now().date())
    df['DIAS EM ABERTO'] = (hoje - df['DATA CRIAÇÃO']).dt.days
    df['DIAS EM ABERTO'] = df['DIAS EM ABERTO'].apply(lambda x: max(0, x))
    
    return df, data_modificacao

# --- Construção da Interface do Dashboard ---
st.title("🎯 Dashboard de Análise de Urgência de SCs")
df, data_att = carregar_dados_do_resumo()

if df.empty:
    st.stop()
if data_att:
    st.markdown(f"**Dados atualizados em:** {data_att.strftime('%d/%m/%Y %H:%M:%S')}")

# --- BARRA LATERAL COM OS FILTROS ---
st.sidebar.header("🔍 Filtros de Análise")
engenheiros = sorted(df['REQUISITANTE'].unique())
engenheiro_selecionado = st.sidebar.selectbox("Filtrar por Engenheiro:", options=["Todos"] + engenheiros)
aprovadores = sorted(df['PENDENTE COM'].unique())
aprovador_selecionado = st.sidebar.selectbox("Filtrar por Aprovador:", options=["Todos"] + aprovadores)
projetos = sorted(df['PROJETO_COMPLETO'].unique())
projeto_selecionado = st.sidebar.selectbox("Filtrar por Projeto:", options=["Todos"] + projetos)

df_filtrado = df
if engenheiro_selecionado != "Todos": df_filtrado = df_filtrado[df_filtrado['REQUISITANTE'] == engenheiro_selecionado]
if aprovador_selecionado != "Todos": df_filtrado = df_filtrado[df_filtrado['PENDENTE COM'] == aprovador_selecionado]
if projeto_selecionado != "Todos": df_filtrado = df_filtrado[df_filtrado['PROJETO_COMPLETO'] == projeto_selecionado]

# --- PÁGINA PRINCIPAL ---
st.markdown("---")
if not df_filtrado.empty:
    tab_valor, tab_ranking, tab_prioridade = st.tabs(["📊 Visão Geral", "🏆 Ranking de Antiguidade", "🎯 Prioridade de Ação"])
    with tab_valor:
        st.subheader("Valor Acumulado por Nível de Urgência")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(label="Valor Total (R$)", value=f"{df_filtrado['VALOR'].sum():,.0f}")
        col2.metric("Total de SCs (Únicas)", df_filtrado['SC'].nunique()) # Usando a contagem correta
        col3.metric("SC Mais Antiga", f"{df_filtrado['DIAS EM ABERTO'].max()} dias")
        with col4:
            opcoes_critico = {'> 15 dias': 15, '> 30 dias': 30, '> 60 dias': 60, '> 90 dias': 90}
            selecao_dias_label = st.selectbox("Criticidade:", options=list(opcoes_critico.keys()), index=2)
            limite_dias_selecionado = opcoes_critico[selecao_dias_label]
            df_criticas = df_filtrado[df_filtrado['DIAS EM ABERTO'] > limite_dias_selecionado]
            st.metric(label=f"SCs Únicas > {limite_dias_selecionado} dias", value=df_criticas['SC'].nunique())
            st.markdown(f"**Valor:** R$ {df_criticas['VALOR'].sum():,.2f}")
        st.markdown("---")
        bins = [-1, 30, 60, 90, float('inf')]; labels = ['Normal (0-30d)', 'Urgente (31-60d)', 'Crítico (61-90d)', 'Muito Crítico (>90d)']
        df_filtrado_copy = df_filtrado.copy()
        df_filtrado_copy['URGÊNCIA'] = pd.cut(df_filtrado_copy['DIAS EM ABERTO'], bins=bins, labels=labels, right=True)
        dados_grafico_valor = df_filtrado_copy.groupby('URGÊNCIA', observed=True).agg(VALOR_TOTAL=('VALOR', 'sum'), CONTAGEM_SC=('SC', 'nunique')).reset_index()
        mapa_cores = {'Normal (0-30d)': 'green', 'Urgente (31-60d)': 'gold', 'Crítico (61-90d)': 'darkorange', 'Muito Crítico (>90d)': 'red'}
        fig_bar_urgencia = px.bar(dados_grafico_valor, x='URGÊNCIA', y='VALOR_TOTAL', labels={'URGÊNCIA': 'Nível de Urgência', 'VALOR_TOTAL': 'Valor Total Parado (R$)'}, text_auto='.2s', color='URGÊNCIA', color_discrete_map=mapa_cores, custom_data=['CONTAGEM_SC'])
        fig_bar_urgencia.update_traces(hovertemplate="<b>%{x}</b><br><br>Valor Total: R$ %{y:,.2f}<br>Quantidade de SCs (Únicas): %{customdata[0]}<extra></extra>")
        fig_bar_urgencia.update_layout(title_text='Valor Parado por Nível de Urgência', yaxis_title="Valor (R$)", xaxis_title="Nível de Urgência")
        fig_bar_urgencia.update_xaxes(categoryorder='array', categoryarray=labels)
        st.plotly_chart(fig_bar_urgencia, use_container_width=True)
    with tab_ranking:
        st.subheader("Top 10 SCs Mais Antigas")
        st.markdown("O **comprimento** da barra indica os dias em aberto. A **cor** indica o valor.")
        top_10_antigas = df_filtrado.sort_values(by='DIAS EM ABERTO', ascending=False).head(10).copy()
        top_10_antigas['LABEL'] = "SC " + top_10_antigas['SC'] + " (" + top_10_antigas['WBS'] + ")"
        fig_ranking = px.bar(top_10_antigas, x='DIAS EM ABERTO', y='LABEL', orientation='h', color='VALOR', color_continuous_scale=px.colors.sequential.Reds, text='DIAS EM ABERTO', hover_data=['PENDENTE COM', 'VALOR', 'REQUISITANTE', 'PROJETO'])
        fig_ranking.update_layout(title="Ranking de SCs por Tempo em Aberto e Valor", xaxis_title="Dias em Aberto", yaxis_title="Solicitação de Compra", yaxis={'categoryorder':'total ascending'}, coloraxis_colorbar=dict(title="Valor (R$)"))
        st.plotly_chart(fig_ranking, use_container_width=True)
    with tab_prioridade:
        st.subheader("Top 10 SCs Mais Críticas por Score")
        st.markdown("Ranking que combina tempo e valor para identificar as principais prioridades.")
        df_com_score = df_filtrado.copy()
        df_com_score['SCORE'] = df_com_score['DIAS EM ABERTO'] * np.log1p(df_com_score['VALOR'])
        top_10_criticos = df_com_score.sort_values(by='SCORE', ascending=False).head(10).copy()
        top_10_criticos['LABEL'] = "SC " + top_10_criticos['SC'] + " (" + top_10_criticos['WBS'] + ")"
        fig_top_10 = px.bar(top_10_criticos, x='SCORE', y='LABEL', orientation='h', color='VALOR', color_continuous_scale=px.colors.sequential.OrRd, text_auto='.2s', title="Top 10 SCs Mais Críticas por Score (Tempo vs. Valor)", labels={'LABEL': 'Solicitação de Compra', 'SCORE': 'Score de Criticidade'}, hover_data=['PENDENTE COM', 'VALOR', 'DIAS EM ABERTO', 'PROJETO'])
        fig_top_10.update_traces(texttemplate='%{x:,.0f}')
        fig_top_10.update_layout(yaxis_title=None, yaxis={'categoryorder':'total ascending'}, coloraxis_colorbar=dict(title="Valor (R$)"))
        st.plotly_chart(fig_top_10, use_container_width=True)
        st.markdown("**Tabela de Detalhes do Top 10**")
        st.dataframe(top_10_criticos[['SC', 'WBS', 'PROJETO', 'DIAS EM ABERTO', 'VALOR', 'REQUISITANTE', 'SCORE']], column_config={"VALOR": st.column_config.NumberColumn(format="R$ %.2f"), "SCORE": st.column_config.NumberColumn(format="%.0f")}, use_container_width=True)
    
    with st.expander("Ver e Exportar Dados Detalhados da Seleção"):
        st.subheader("Dados Completos")
        colunas_para_exibir = [col for col in df.columns if col not in ['PROJETO_COMPLETO', 'SC_WBS']]
        st.dataframe(df_filtrado.sort_values(by='DIAS EM ABERTO', ascending=False)[colunas_para_exibir])
        @st.cache_data
        def convert_df_to_csv(df_to_convert):
            return df_to_convert.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        st.download_button(label="📥 Baixar dados filtrados como CSV", data=convert_df_to_csv(df_filtrado[colunas_para_exibir]), file_name='analise_urgencia_sc.csv', mime='text/csv')
else:
    st.warning("Nenhum dado encontrado para a combinação de filtros selecionada.")