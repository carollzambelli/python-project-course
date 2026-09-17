"""Constantes centrais do pipeline: cidades, caminhos e configuração via ambiente."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Lê o arquivo .env (se existir, na raiz do projeto) e coloca suas variáveis
# em os.environ — assim os.getenv(...) abaixo enxerga tanto variáveis
# definidas no .env quanto as já existentes no ambiente do sistema.
load_dotenv()

# --- Caminhos -----------------------------------------------------------
# __file__ é o caminho deste arquivo (config.py); .resolve() o transforma em
# caminho absoluto; .parents[2] sobe 2 pastas (clima_pipeline/ -> src/ ->
# raiz do projeto). Assim BASE_DIR funciona não importa de onde o script é
# chamado — não dependemos do diretório atual do terminal.
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"  # JSON bruto salvo por pipeline.py, um arquivo por cidade
PROCESSED_DIR = DATA_DIR / "processed"  # saídas intermediárias usadas pelos notebooks
# CLIMA_DB_PATH permite trocar o caminho do banco (ex.: em testes) sem mexer
# no código — se a variável de ambiente não existir, usa o caminho padrão.
DB_PATH = Path(os.getenv("CLIMA_DB_PATH", DATA_DIR / "clima.db"))

# Garante que essas pastas existam antes de qualquer código tentar escrever
# nelas (parents=True cria pastas intermediárias; exist_ok=True não reclama
# se a pasta já existir).
for _dir in (RAW_DIR, PROCESSED_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# --- Open-Meteo -----------------------------------------------------------
# URL da Historical Weather API do Open-Meteo (dados horários históricos).
# Vem de variável de ambiente para poder apontar para outro servidor em
# testes, sem editar código.
OPENMETEO_BASE_URL = os.getenv(
    "OPENMETEO_BASE_URL", "https://archive-api.open-meteo.com/v1/archive"
)
# Quais variáveis climáticas horárias pedimos à API — usado em
# extract/open_meteo_client.py para montar o parâmetro "hourly" da requisição.
VARIAVEIS_HORARIAS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
]
TIMEZONE = "America/Sao_Paulo"  # fuso usado para converter os horários devolvidos pela API

# --- Cidades ---------------------------------------------------------------
# slug -> metadados usados tanto na extração (lat/lon) quanto na API/dashboard
# (nome_exibicao/uf/regiao).
CIDADES = {
    "sao_paulo": {
        "nome_exibicao": "São Paulo",
        "lat": -23.5505,
        "lon": -46.6333,
        "uf": "SP",
        "regiao": "Sudeste",
    },
    "rio_de_janeiro": {
        "nome_exibicao": "Rio de Janeiro",
        "lat": -22.9068,
        "lon": -43.1729,
        "uf": "RJ",
        "regiao": "Sudeste",
    },
    "manaus": {
        "nome_exibicao": "Manaus",
        "lat": -3.1190,
        "lon": -60.0217,
        "uf": "AM",
        "regiao": "Norte",
    },
    "porto_alegre": {
        "nome_exibicao": "Porto Alegre",
        "lat": -30.0346,
        "lon": -51.2177,
        "uf": "RS",
        "regiao": "Sul",
    },
    "recife": {
        "nome_exibicao": "Recife",
        "lat": -8.0476,
        "lon": -34.8770,
        "uf": "PE",
        "regiao": "Nordeste",
    },
}

# Período padrão usado quando ninguém especifica datas (CLI do pipeline,
# dashboard). Ficam aqui, e não espalhados pelo código, para mudar em um
# único lugar.
DATA_INICIO_PADRAO = os.getenv("CLIMA_DATA_INICIO", "2025-01-01")
DATA_FIM_PADRAO = os.getenv("CLIMA_DATA_FIM", "2025-01-31")

# --- API / dashboard ---------------------------------------------------------------
API_HOST = os.getenv("CLIMA_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("CLIMA_API_PORT", "8000"))
# Endereço completo que o dashboard Streamlit usa para chamar a API — pode
# ser sobrescrito direto (CLIMA_API_BASE_URL) se a API rodar em outra
# máquina/porta, sem precisar recalcular a partir de host+porta.
API_BASE_URL = os.getenv("CLIMA_API_BASE_URL", f"http://{API_HOST}:{API_PORT}")

# --- Logging ----------------------------------------------------------------
# Configuração mínima: uma linha por log, com data/hora, nível e a mensagem,
# escrita no console. logging.basicConfig só tem efeito na primeira vez que é
# chamado (chamadas seguintes, inclusive de outros módulos que importam este
# arquivo, são ignoradas) — por isso não precisamos de nenhuma trava manual
# para evitar configurar duas vezes.
LOG_LEVEL = os.getenv("CLIMA_LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

def resolver_slug_cidade(identificador: str) -> str | None:
    """Aceita slug, nome de exibição ou UF e devolve o slug correspondente.

    Existe porque a API recebe o nome da cidade como texto vindo de fora
    (query string) e o usuário pode digitar de formas diferentes: o slug
    interno ("sao_paulo"), o nome bonito ("São Paulo") ou a UF ("SP"). Esta
    função tenta as três formas e devolve sempre o slug — que é a chave usada
    internamente em CIDADES e nas tabelas do banco.
    """
    # .strip() remove espaços acidentais; .lower() torna a busca
    # case-insensitive (não importa se o usuário digitou "SP" ou "sp").
    identificador_normalizado = identificador.strip().lower()

    # Caso mais comum: já é o próprio slug (ex.: "sao_paulo").
    if identificador_normalizado in CIDADES:
        return identificador_normalizado

    # Senão, tenta casar por UF ou por nome de exibição.
    for slug, info in CIDADES.items():
        if identificador_normalizado == info["uf"].lower():
            return slug
        if identificador_normalizado == info["nome_exibicao"].lower():
            return slug

    # Nenhuma das três formas bateu — quem chamou decide o que fazer com
    # None (a API, por exemplo, transforma isso em um erro 404).
    return None


if __name__ == "__main__":
    # Entrada mockada: roda `python -m clima_pipeline.config` para testar
    # resolver_slug_cidade() isoladamente (slug, UF, nome de exibição e um
    # valor inexistente), sem precisar da API nem do banco.
    entradas_mock = ["sao_paulo", "SP", "Rio de Janeiro", "cidade_inexistente"]
    for entrada in entradas_mock:
        print(f"{entrada} -> {resolver_slug_cidade(entrada)!r}")
