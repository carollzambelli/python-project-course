"""Transforma o JSON bruto do Open-Meteo em um DataFrame horário tratado."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Mapeia os nomes de coluna que vêm da API do Open-Meteo (em inglês, formato
# técnico) para nomes em português mais legíveis no resto do projeto (API,
# dashboard, banco de dados). Esse rename só acontece no fim de clean(),
# em _padronizar_colunas — por isso, as funções chamadas ANTES dela (como
# _tratar_faltantes) ainda enxergam os nomes originais da API.
_RENOMEIA_COLUNAS = {
    "temperature_2m": "temp_c",
    "relative_humidity_2m": "umidade_pct",
    "precipitation": "precipitacao_mm",
    "wind_speed_10m": "vento_kmh",
}

# Colunas em que faz sentido "preencher o buraco" com interpolação linear
# (temperatura e umidade variam suavemente hora a hora, então o valor que
# falta pode ser estimado a partir dos vizinhos). Importante: como
# _tratar_faltantes roda ANTES do rename (veja clean()), aqui usamos os
# nomes ORIGINAIS da API (temperature_2m/relative_humidity_2m), não os
# nomes finais (temp_c/umidade_pct) — usar os nomes finais aqui faria a
# interpolação nunca rodar, porque a coluna com esse nome ainda não existe
# neste ponto do pipeline.
_COLUNAS_INTERPOLAVEIS = ["temperature_2m", "relative_humidity_2m"]


class ClimaCleaner:
    """Responsável por transformar o JSON bruto em DataFrame tratado."""

    def clean(self, raw_data: dict, city: str) -> pd.DataFrame:
        # raw_data é o dict devolvido pela API do Open-Meteo (veja
        # OpenMeteoClient.fetch_historical): raw_data["hourly"] é um dict de
        # listas, uma lista por variável (time, temperature_2m, ...), todas
        # do mesmo tamanho. pd.DataFrame(...) transforma isso direto numa
        # tabela, uma coluna por variável.
        df = pd.DataFrame(raw_data["hourly"])
        df["cidade"] = city  # guarda de qual cidade são esses dados (a API não devolve isso)
        df["datetime"] = pd.to_datetime(df["time"])  # texto ISO -> datetime real do pandas
        df = df.drop(columns=["time"])  # "time" virou "datetime", não precisamos mais dele

        # Pipeline de limpeza em etapas — cada função cuida de um problema
        # específico dos dados e devolve o DataFrame já corrigido para a
        # próxima etapa. A ordem importa: outliers e valores faltantes
        # precisam ser tratados enquanto as colunas ainda têm os nomes
        # originais da API (veja os comentários em _COLUNAS_INTERPOLAVEIS),
        # e o rename (_padronizar_colunas) fica por último.
        df = self._remover_duplicatas(df)
        df = self._tratar_faltantes(df)
        df = self._tratar_outliers(df, coluna="wind_speed_10m")
        df = self._padronizar_colunas(df)

        # Devolve só as colunas que o resto do projeto (API, banco, dashboard)
        # espera, já ordenado por cidade e data/hora — deixa o DataFrame
        # pronto para ser concatenado com o de outras cidades em pipeline.py.
        colunas = ["cidade", "datetime", "temp_c", "umidade_pct", "precipitacao_mm", "vento_kmh"]
        return df[colunas].sort_values(["cidade", "datetime"]).reset_index(drop=True)

    def _remover_duplicatas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove linhas repetidas para a mesma cidade+horário (a API pode devolver isso)."""
        duplicados = df.duplicated(subset=["cidade", "datetime"])
        if duplicados.any():
            logger.warning("Removendo %d linhas duplicadas (cidade, datetime)", duplicados.sum())
            df = df[~duplicados]
        return df

    def _tratar_faltantes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preenche valores ausentes (NaN) antes de seguir para o resto do pipeline."""
        # Precisa estar ordenado por tempo para a interpolação linear fazer
        # sentido (ela olha o valor anterior e o seguinte na linha do tempo).
        df = df.sort_values("datetime").copy()

        for coluna in _COLUNAS_INTERPOLAVEIS:
            if coluna in df.columns:
                # interpolate: estima o valor faltante com base nos vizinhos.
                # ffill/bfill: cobre os casos em que falta o começo ou o fim
                # da série (a interpolação sozinha não sabe extrapolar).
                df[coluna] = df[coluna].interpolate(method="linear").ffill().bfill()

        if "precipitation" in df.columns:
            # Chuva não se interpola (não existe "meia chuva" entre duas
            # horas) — se o valor vier ausente/inválido, assumimos 0.0 mm.
            df["precipitation"] = pd.to_numeric(df["precipitation"], errors="coerce").fillna(0.0)

        return df

    def _tratar_outliers(self, df: pd.DataFrame, coluna: str) -> pd.DataFrame:
        """Detecta outliers pelo método do IQR (intervalo interquartil) e os corrige por interpolação."""
        serie = df[coluna]
        q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
        iqr = q3 - q1
        # Regra clássica de outlier: qualquer valor 1.5x o IQR além do
        # 1º/3º quartil é tratado como leitura suspeita do sensor (ex.: um
        # pico de vento absurdo), não como um evento real.
        limite_inferior, limite_superior = q1 - 1.5 * iqr, q3 + 1.5 * iqr

        mascara = (serie < limite_inferior) | (serie > limite_superior)
        if mascara.any():
            logger.warning("Corrigindo %d outlier(s) em '%s' via interpolação", mascara.sum(), coluna)
            # Descarta o outlier (vira NaN) e deixa a interpolação linear
            # estimar um valor mais plausível a partir dos vizinhos.
            df.loc[mascara, coluna] = np.nan
            df[coluna] = df[coluna].interpolate(method="linear").ffill().bfill()

        return df

    def _padronizar_colunas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Último passo: troca os nomes técnicos da API pelos nomes finais em português."""
        return df.rename(columns=_RENOMEIA_COLUNAS)


if __name__ == "__main__":
    # Entrada mockada: simula o JSON que a API do Open-Meteo devolveria (com
    # um valor faltante e um outlier propositais) para testar clean()
    # isoladamente, sem chamar a API de verdade.
    raw_mock = {
        "hourly": {
            "time": [f"2025-01-01T0{h}:00" for h in range(8)],
            "temperature_2m": [22.5, None, 21.8, 22.0, 21.5, 22.2, 21.9, 22.1],
            "relative_humidity_2m": [80, 81, 83, 82, 79, 80, 81, 82],
            "precipitation": [0.0, 0.0, 1.2, 0.0, 0.0, 0.0, 0.0, 0.0],
            # Vento com 7 valores "normais" e 1 outlier proposital (500) — o
            # detector de outliers (IQR) precisa de várias amostras normais
            # para estabelecer uma faixa estável; com poucos pontos, o
            # próprio outlier distorce os quartis e passa despercebido.
            "wind_speed_10m": [10.2, 9.8, 11.0, 9.5, 10.5, 10.0, 9.9, 500.0],
        }
    }
    print(ClimaCleaner().clean(raw_mock, city="sao_paulo"))
