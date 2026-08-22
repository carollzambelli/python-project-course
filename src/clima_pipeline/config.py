"""Constantes centrais do pipeline: cidades, caminhos e configuração via ambiente."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Caminhos -----------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = Path(os.getenv("CLIMA_DB_PATH", DATA_DIR / "clima.db"))
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "pipeline.log"

for _dir in (RAW_DIR, PROCESSED_DIR, LOGS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# --- Open-Meteo -----------------------------------------------------------
OPENMETEO_BASE_URL = os.getenv(
    "OPENMETEO_BASE_URL", "https://archive-api.open-meteo.com/v1/archive"
)
VARIAVEIS_HORARIAS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
]
TIMEZONE = "America/Sao_Paulo"

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

DATA_INICIO_PADRAO = os.getenv("CLIMA_DATA_INICIO", "2025-01-01")
DATA_FIM_PADRAO = os.getenv("CLIMA_DATA_FIM", "2025-01-31")

# --- API / dashboard ---------------------------------------------------------------
API_HOST = os.getenv("CLIMA_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("CLIMA_API_PORT", "8000"))
API_BASE_URL = os.getenv("CLIMA_API_BASE_URL", f"http://{API_HOST}:{API_PORT}")

LOG_LEVEL = os.getenv("CLIMA_LOG_LEVEL", "INFO")


def resolver_slug_cidade(identificador: str) -> str | None:
    """Aceita slug, nome de exibição ou UF e devolve o slug correspondente."""
    identificador_normalizado = identificador.strip().lower()

    if identificador_normalizado in CIDADES:
        return identificador_normalizado

    for slug, info in CIDADES.items():
        if identificador_normalizado == info["uf"].lower():
            return slug
        if identificador_normalizado == info["nome_exibicao"].lower():
            return slug

    return None
