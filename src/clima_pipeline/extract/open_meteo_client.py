"""Cliente HTTP para a Historical Weather API do Open-Meteo."""

import logging

import requests

from clima_pipeline.config import CIDADES, OPENMETEO_BASE_URL, TIMEZONE, VARIAVEIS_HORARIAS

logger = logging.getLogger(__name__)


class OpenMeteoClient:
    """Responsável apenas por falar com a API (extração).

    Esta classe não trata nem interpreta os dados — só sabe montar a
    requisição HTTP certa e devolver o JSON puro que a API respondeu. Quem
    limpa/interpreta esse JSON é a camada de transform (ClimaCleaner).
    """

    def __init__(self, base_url: str = OPENMETEO_BASE_URL, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        # Usar uma Session (em vez de requests.get direto) reaproveita a
        # conexão TCP entre requisições — como o pipeline faz uma chamada
        # por cidade, isso evita reabrir conexão a cada uma.
        self._session = requests.Session()

    def fetch_historical(self, city: str, start: str, end: str) -> dict:
        """Busca o histórico horário de uma cidade cadastrada em `config.CIDADES`.

        `city` é o slug da cidade (ex.: "sao_paulo"). Lança `KeyError` se o slug
        não estiver cadastrado e `requests.HTTPError` se a API responder com erro.
        """
        if city not in CIDADES:
            # Falha rápido e com mensagem clara em vez de deixar o KeyError
            # "cru" do dicionário (que só diria a chave, sem sugerir opções).
            raise KeyError(
                f"Cidade '{city}' não está cadastrada em config.CIDADES. "
                f"Cidades disponíveis: {sorted(CIDADES)}"
            )

        # Traduz o slug para lat/lon (a API do Open-Meteo trabalha com
        # coordenadas, não com nomes de cidade) e delega para o método que
        # sabe montar a requisição.
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
            # A API espera as variáveis horárias como uma string separada
            # por vírgula (ex.: "temperature_2m,relative_humidity_2m,...").
            "hourly": ",".join(VARIAVEIS_HORARIAS),
            "timezone": TIMEZONE,
        }
        resposta = self._session.get(self.base_url, params=params, timeout=self.timeout)
        # Se a API responder com erro HTTP (4xx/5xx), levanta uma exceção
        # aqui mesmo — decidir o que fazer com esse erro (logar, tentar de
        # novo, etc.) é responsabilidade de quem chamou fetch_historical,
        # não desta camada de extração.
        resposta.raise_for_status()
        return resposta.json()


if __name__ == "__main__":
    # Entrada mockada: substitui a sessão HTTP por uma resposta falsa, para
    # testar fetch_historical() sem depender de rede nem da API real.
    from unittest.mock import MagicMock

    resposta_mock = MagicMock()
    resposta_mock.raise_for_status.return_value = None
    resposta_mock.json.return_value = {
        "hourly": {
            "time": ["2025-01-01T00:00", "2025-01-01T01:00"],
            "temperature_2m": [22.5, 22.1],
            "relative_humidity_2m": [80, 82],
            "precipitation": [0.0, 0.0],
            "wind_speed_10m": [10.2, 9.8],
        }
    }

    client = OpenMeteoClient()
    client._session.get = MagicMock(return_value=resposta_mock)

    resultado = client.fetch_historical("sao_paulo", "2025-01-01", "2025-01-01")
    print(resultado)
