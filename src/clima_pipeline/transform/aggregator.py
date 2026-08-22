"""Cria a visão diária agregada e features derivadas a partir do dado horário tratado."""

import pandas as pd


def _classificar_temperatura(temp_media: float) -> str:
    if temp_media < 18:
        return "frio"
    elif temp_media < 26:
        return "ameno"
    return "quente"


def _calcular_indice_conforto(row: pd.Series) -> float:
    temp, umidade = row["temp_media"], row["umidade_media"]
    if temp < 27:
        return round(temp, 1)

    # Heat index simplificado (Rothfusz), em Celsius
    indice = (
        -8.784
        + 1.611 * temp
        + 2.339 * umidade
        - 0.146 * temp * umidade
        + -1.230e-2 * temp**2
        + -1.642e-2 * umidade**2
        + 2.212e-3 * temp**2 * umidade
        + 7.255e-4 * temp * umidade**2
        + -3.582e-6 * temp**2 * umidade**2
    )
    return round(indice, 1)


class ClimaAggregator:
    """Cria a visão agregada/derivada dos dados."""

    def build_daily_view(self, df: pd.DataFrame) -> pd.DataFrame:
        diario = (
            df.groupby(["cidade", pd.Grouper(key="datetime", freq="D")])
            .agg(
                temp_media=("temp_c", "mean"),
                temp_min=("temp_c", "min"),
                temp_max=("temp_c", "max"),
                umidade_media=("umidade_pct", "mean"),
                precipitacao_total=("precipitacao_mm", "sum"),
                vento_medio=("vento_kmh", "mean"),
            )
            .reset_index()
            .rename(columns={"datetime": "data"})
        )
        diario["data"] = diario["data"].dt.date
        diario = diario.sort_values(["cidade", "data"]).reset_index(drop=True)

        diario["categoria_temp"] = diario["temp_media"].apply(_classificar_temperatura)
        diario["categoria_chuva"] = diario["precipitacao_total"].apply(
            lambda mm: "chuvoso" if mm > 1.0 else "seco"
        )

        diario["media_movel_3d"] = diario.groupby("cidade")["temp_media"].transform(
            lambda s: s.rolling(window=3, min_periods=1).mean()
        )
        diario["media_movel_7d"] = diario.groupby("cidade")["temp_media"].transform(
            lambda s: s.rolling(window=7, min_periods=1).mean()
        )

        diario["ranking_temp_dia"] = diario.groupby("data")["temp_media"].rank(
            ascending=False, method="min"
        ).astype(int)

        diario["indice_conforto_c"] = diario.apply(_calcular_indice_conforto, axis=1)

        return diario

    def build_pivot(self, diario: pd.DataFrame, valor: str = "temp_media") -> pd.DataFrame:
        """Tabela pivotada: linhas = data, colunas = cidade, valores = `valor`."""
        return pd.pivot_table(diario, index="data", columns="cidade", values=valor)
