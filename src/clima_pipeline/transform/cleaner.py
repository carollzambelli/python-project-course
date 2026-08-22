"""Transforma o JSON bruto do Open-Meteo em um DataFrame horário tratado."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_RENOMEIA_COLUNAS = {
    "temperature_2m": "temp_c",
    "relative_humidity_2m": "umidade_pct",
    "precipitation": "precipitacao_mm",
    "wind_speed_10m": "vento_kmh",
}

_COLUNAS_INTERPOLAVEIS = ["temp_c", "umidade_pct"]


class ClimaCleaner:
    """Responsável por transformar o JSON bruto em DataFrame tratado."""

    def clean(self, raw_data: dict, city: str) -> pd.DataFrame:
        df = pd.DataFrame(raw_data["hourly"])
        df["cidade"] = city
        df["datetime"] = pd.to_datetime(df["time"])
        df = df.drop(columns=["time"])

        df = self._remover_duplicatas(df)
        df = self._tratar_faltantes(df)
        df = self._tratar_outliers(df, coluna="wind_speed_10m")
        df = self._padronizar_colunas(df)

        colunas = ["cidade", "datetime", "temp_c", "umidade_pct", "precipitacao_mm", "vento_kmh"]
        return df[colunas].sort_values(["cidade", "datetime"]).reset_index(drop=True)

    def _remover_duplicatas(self, df: pd.DataFrame) -> pd.DataFrame:
        duplicados = df.duplicated(subset=["cidade", "datetime"])
        if duplicados.any():
            logger.warning("Removendo %d linhas duplicadas (cidade, datetime)", duplicados.sum())
            df = df[~duplicados]
        return df

    def _tratar_faltantes(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values("datetime").copy()

        for coluna in _COLUNAS_INTERPOLAVEIS:
            if coluna in df.columns:
                df[coluna] = df[coluna].interpolate(method="linear").ffill().bfill()

        if "precipitation" in df.columns:
            df["precipitation"] = pd.to_numeric(df["precipitation"], errors="coerce").fillna(0.0)

        return df

    def _tratar_outliers(self, df: pd.DataFrame, coluna: str) -> pd.DataFrame:
        serie = df[coluna]
        q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
        iqr = q3 - q1
        limite_inferior, limite_superior = q1 - 1.5 * iqr, q3 + 1.5 * iqr

        mascara = (serie < limite_inferior) | (serie > limite_superior)
        if mascara.any():
            logger.warning("Corrigindo %d outlier(s) em '%s' via interpolação", mascara.sum(), coluna)
            df.loc[mascara, coluna] = np.nan
            df[coluna] = df[coluna].interpolate(method="linear").ffill().bfill()

        return df

    def _padronizar_colunas(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.rename(columns=_RENOMEIA_COLUNAS)
