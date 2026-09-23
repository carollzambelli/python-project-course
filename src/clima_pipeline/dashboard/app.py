"""Dashboard Streamlit — consome a REST API (não acessa o SQLite diretamente).

Importante para entender a arquitetura: este arquivo nunca importa
SQLiteRepository nem ClimaCleaner/ClimaAggregator — ele só faz requisições
HTTP para a API (clima_pipeline.api.main). Isso significa que o dashboard
pode rodar numa máquina diferente da API, e que trocar como os dados são
guardados no banco não exige tocar neste arquivo.
"""

import datetime as dt

import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

from clima_pipeline.config import API_BASE_URL, DATA_FIM_PADRAO, DATA_INICIO_PADRAO

st.set_page_config(page_title="Clima Pipeline", layout="wide")
st.title("Clima Pipeline — Dashboard")

# Barra lateral: controles que o usuário pode mudar a qualquer momento e que
# afetam o resto da página (Streamlit reexecuta o script inteiro a cada
# interação, de cima para baixo).
with st.sidebar:
    api_base_url = st.text_input("URL da API", value=API_BASE_URL)
    inicio = st.date_input("Data inicial", value=dt.date.fromisoformat(DATA_INICIO_PADRAO))
    fim = st.date_input("Data final", value=dt.date.fromisoformat(DATA_FIM_PADRAO))


@st.cache_data(ttl=300)
def carregar_cidades(base_url: str) -> pd.DataFrame:
    """Busca a lista de cidades na API. Cacheada por 5 min (muda raramente)."""
    resposta = requests.get(f"{base_url}/cidades", timeout=10)
    resposta.raise_for_status()
    return pd.DataFrame(resposta.json())


@st.cache_data(ttl=60)
def carregar_diario(base_url: str, slug: str, inicio: dt.date, fim: dt.date) -> pd.DataFrame:
    """Busca a visão diária de UMA cidade na API. Cacheada por 1 min.

    @st.cache_data guarda o resultado por combinação de argumentos — trocar
    de cidade ou de data dispara uma chamada nova; repetir a mesma
    combinação dentro da janela de cache reaproveita o resultado, sem bater
    na API de novo a cada interação do usuário na página.
    """
    params = {"cidade": slug, "inicio": str(inicio), "fim": str(fim)}
    resposta = requests.get(f"{base_url}/clima/diario", params=params, timeout=10)
    resposta.raise_for_status()
    df = pd.DataFrame(resposta.json())
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
    return df


# Primeira chamada à API: se ela falhar (API fora do ar, URL errada), mostra
# uma mensagem amigável e para a execução do script aqui (st.stop()) em vez
# de deixar o Streamlit quebrar com uma stack trace para o usuário.
try:
    cidades_df = carregar_cidades(api_base_url)
except requests.RequestException as erro:
    st.error(f"Não foi possível falar com a API em '{api_base_url}': {erro}")
    st.stop()

# Dicionários auxiliares para converter entre o slug (usado nas chamadas de
# API) e o nome de exibição (o que o usuário vê e escolhe na tela).
nome_por_slug = dict(zip(cidades_df["slug"], cidades_df["nome_exibicao"]))
slug_por_nome = dict(zip(cidades_df["nome_exibicao"], cidades_df["slug"]))

with st.sidebar:
    nomes_selecionados = st.multiselect(
        "Cidades", options=list(slug_por_nome), default=list(slug_por_nome)[:3]
    )

if not nomes_selecionados:
    st.info("Selecione ao menos uma cidade na barra lateral.")
    st.stop()

slugs_selecionados = [slug_por_nome[nome] for nome in nomes_selecionados]

# Busca o diário de cada cidade selecionada (uma chamada de API por cidade).
# Cada chamada é tentada separadamente: se a API falhar para UMA cidade
# (timeout, erro passageiro), mostramos um aviso só daquela cidade e
# seguimos com as demais, em vez de derrubar o dashboard inteiro.
partes = []
for slug in slugs_selecionados:
    try:
        partes.append(carregar_diario(api_base_url, slug, inicio, fim))
    except requests.RequestException as erro:
        st.warning(f"Não foi possível carregar dados de {nome_por_slug[slug]}: {erro}")

diario = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()

if diario.empty:
    st.warning("Sem dados para o período/cidades selecionados.")
    st.stop()

diario["nome_exibicao"] = diario["cidade"].map(nome_por_slug)

# --- Gráfico 1: temperatura diária + média móvel, uma linha por cidade ---
st.subheader("Temperatura ao longo do tempo (diária vs. média móvel de 7 dias)")
fig, ax = plt.subplots(figsize=(11, 4))
for slug in slugs_selecionados:
    subset = diario[diario["cidade"] == slug]
    nome = nome_por_slug[slug]
    # A curva diária "crua" (alpha baixo, mais apagada) mostra o ruído dia a
    # dia; a média móvel de 7 dias (mais grossa) mostra a tendência por trás
    # do ruído — as duas juntas contam a história completa.
    ax.plot(subset["data"], subset["temp_media"], alpha=0.35, label=f"{nome} (diária)")
    ax.plot(subset["data"], subset["media_movel_7d"], linewidth=2, label=f"{nome} (móvel 7d)")
ax.set_xlabel("Data")
ax.set_ylabel("Temperatura (°C)")
ax.legend(fontsize=8)
fig.autofmt_xdate(rotation=45)  # inclina as datas no eixo X para não sobrepor
st.pyplot(fig)

# --- Gráfico 2: comparação direta entre cidades, para a variável escolhida ---
st.subheader("Comparativo entre cidades")
variavel = st.selectbox(
    "Variável",
    ["temp_media", "umidade_media", "precipitacao_total", "vento_medio", "indice_conforto_c"],
    index=0,
)
# Já temos os dados de todas as cidades selecionadas em `diario` (buscados
# acima) — não precisamos de outra chamada à API só para comparar. pivot_table
# reorganiza o mesmo DataFrame: uma coluna por cidade, indexada pela data,
# exatamente o formato que st.line_chart espera para desenhar uma linha por
# cidade.
comparativo_df = diario.pivot_table(index="data", columns="nome_exibicao", values=variavel)
if comparativo_df.empty:
    st.info("Sem dados comparativos para essa combinação.")
else:
    st.line_chart(comparativo_df)

# --- Tabela final: os mesmos dados do gráfico 1, em formato de tabela ---
st.subheader("Tabela agregada (visão diária)")
colunas_tabela = [
    "nome_exibicao", "data", "temp_media", "temp_min", "temp_max", "umidade_media",
    "precipitacao_total", "categoria_temp", "categoria_chuva", "indice_conforto_c",
]
st.dataframe(
    diario[colunas_tabela].sort_values(["nome_exibicao", "data"]),
    width="stretch",
    hide_index=True,
)
