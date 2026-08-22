"""Cliente HTTP para a Historical Weather API do Open-Meteo."""

import logging

import requests

from clima_pipeline.config import CIDADES, OPENMETEO_BASE_URL, TIMEZONE, VARIAVEIS_HORARIAS

logger = logging.getLogger(__name__)


class OpenMeteoClient:
    """Responsável apenas por falar com a API (extração)."""

    def __init__(self, base_url: str = OPENMETEO_BASE_URL, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self._session = requests.Session()

    def fetch_historical(self, city: str, start: str, end: str) -> dict:
        """Busca o histórico horário de uma cidade cadastrada em `config.CIDADES`.

        `city` é o slug da cidade (ex.: "sao_paulo"). Lança `KeyError` se o slug
        não estiver cadastrado e `requests.HTTPError` se a API responder com erro.
        """
        if city not in CIDADES:
            raise KeyError(
                f"Cidade '{city}' não está cadastrada em config.CIDADES. "
                f"Cidades disponíveis: {sorted(CIDADES)}"
            )

        info = CIDADES[city]
        logger.info("Buscando clima de %s (%s a %s)", info["nome_exibicao"], start, end)
        return self.fetch_by_coordinates(info["lat"], info["lon"], start, end)

    def fetch_by_coordinates(self, lat: float, lon: float, start: str, end: str) -> dict:
        """Busca o histórico horário para um ponto (lat, lon) arbitrário."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start,
            "end_date": end,
            "hourly": ",".join(VARIAVEIS_HORARIAS),
            "timezone": TIMEZONE,
        }
        resposta = self._session.get(self.base_url, params=params, timeout=self.timeout)
        resposta.raise_for_status()
        return resposta.json()

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "OpenMeteoClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
