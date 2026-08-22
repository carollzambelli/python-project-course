"""Dashboard Streamlit — consome a REST API (não acessa o SQLite diretamente)."""

import datetime as dt

import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

from clima_pipeline.config import API_BASE_URL, DATA_FIM_PADRAO, DATA_INICIO_PADRAO

st.set_page_config(page_title="Clima Pipeline", layout="wide")
st.title("Clima Pipeline — Dashboard")

with st.sidebar:
    api_base_url = st.text_input("URL da API", value=API_BASE_URL)
    inicio = st.date_input("Data inicial", value=dt.date.fromisoformat(DATA_INICIO_PADRAO))
    fim = st.date_input("Data final", value=dt.date.fromisoformat(DATA_FIM_PADRAO))


@st.cache_data(ttl=300)
def carregar_cidades(base_url: str) -> pd.DataFrame:
    resposta = requests.get(f"{base_url}/cidades", timeout=10)
    resposta.raise_for_status()
    return pd.DataFrame(resposta.json())


@st.cache_data(ttl=60)
def carregar_diario(base_url: str, slug: str, inicio: dt.date, fim: dt.date) -> pd.DataFrame:
    params = {"cidade": slug, "inicio": str(inicio), "fim": str(fim)}
    resposta = requests.get(f"{base_url}/clima/diario", params=params, timeout=10)
    resposta.raise_for_status()
    df = pd.DataFrame(resposta.json())
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
    return df


@st.cache_data(ttl=60)
def carregar_comparativo(base_url: str, slugs: list[str], variavel: str) -> pd.DataFrame:
    params = {"cidades": ",".join(slugs), "variavel": variavel}
    resposta = requests.get(f"{base_url}/clima/comparativo", params=params, timeout=10)
    resposta.raise_for_status()
    df = pd.DataFrame(resposta.json()["registros"])
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
        df = df.set_index("data")
    return df


try:
    cidades_df = carregar_cidades(api_base_url)
except requests.RequestException as erro:
    st.error(f"Não foi possível falar com a API em '{api_base_url}': {erro}")
    st.stop()

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

diario = pd.concat(
    [carregar_diario(api_base_url, slug, inicio, fim) for slug in slugs_selecionados],
    ignore_index=True,
)

if diario.empty:
    st.warning("Sem dados para o período/cidades selecionados.")
    st.stop()

diario["nome_exibicao"] = diario["cidade"].map(nome_por_slug)

st.subheader("Temperatura ao longo do tempo (diária vs. média móvel de 7 dias)")
fig, ax = plt.subplots(figsize=(11, 4))
for slug in slugs_selecionados:
    subset = diario[diario["cidade"] == slug]
    nome = nome_por_slug[slug]
    ax.plot(subset["data"], subset["temp_media"], alpha=0.35, label=f"{nome} (diária)")
    ax.plot(subset["data"], subset["media_movel_7d"], linewidth=2, label=f"{nome} (móvel 7d)")
ax.set_xlabel("Data")
ax.set_ylabel("Temperatura (°C)")
ax.legend(fontsize=8)
fig.autofmt_xdate(rotation=45)
st.pyplot(fig)

st.subheader("Comparativo entre cidades")
variavel = st.selectbox(
    "Variável",
    ["temp_media", "umidade_media", "precipitacao_total", "vento_medio", "indice_conforto_c"],
    index=0,
)
comparativo_df = carregar_comparativo(api_base_url, slugs_selecionados, variavel)
if comparativo_df.empty:
    st.info("Sem dados comparativos para essa combinação.")
else:
    st.line_chart(comparativo_df)

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
