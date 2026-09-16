"""Cria a visão diária agregada e features derivadas a partir do dado horário tratado."""

import pandas as pd


def _classificar_temperatura(temp_media: float) -> str:
    """Regra simples de negócio: transforma um número em um rótulo legível para o dashboard."""
    if temp_media < 18:
        return "frio"
    elif temp_media < 26:
        return "ameno"
    return "quente"


def _calcular_indice_conforto(row: pd.Series) -> float:
    """Sensação térmica aproximada, combinando temperatura e umidade.

    Abaixo de 27°C a própria temperatura já é uma boa estimativa da sensação
    térmica (o efeito da umidade é pequeno demais para importar). Acima
    disso, usamos o heat index simplificado (fórmula de Rothfusz, em
    Celsius): quanto mais quente E mais úmido, maior a sensação térmica em
    relação à temperatura real — é por isso que 30°C num dia úmido "pesa"
    mais do que 30°C num dia seco.
    """
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
        """Recebe o DataFrame horário (uma linha por hora) e devolve uma visão diária.

        `df` deve ter as colunas produzidas por ClimaCleaner.clean(): cidade,
        datetime, temp_c, umidade_pct, precipitacao_mm, vento_kmh — de uma ou
        várias cidades concatenadas.
        """
        # pd.Grouper(freq="D") agrupa por dia dentro de cada cidade — ou
        # seja, uma linha de saída por (cidade, dia). .agg(...) calcula uma
        # métrica por coluna horária (média, mínimo, máximo, soma).
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
            .reset_index()  # tira cidade/data do índice e volta a serem colunas normais
            .rename(columns={"datetime": "data"})
        )
        diario["data"] = diario["data"].dt.date  # não precisamos mais da hora, só do dia
        diario = diario.sort_values(["cidade", "data"]).reset_index(drop=True)

        # --- colunas derivadas: cada uma adiciona uma "leitura" diferente sobre o mesmo dado ---

        # Rótulo de temperatura (frio/ameno/quente) — mais fácil de mostrar
        # no dashboard do que pedir para o usuário interpretar um número.
        diario["categoria_temp"] = diario["temp_media"].apply(_classificar_temperatura)
        # Rótulo de chuva — usamos 1.0mm como limiar mínimo para considerar
        # "chuvoso" (valores menores costumam ser ruído do sensor/garoa).
        diario["categoria_chuva"] = diario["precipitacao_total"].apply(
            lambda mm: "chuvoso" if mm > 1.0 else "seco"
        )

        # Médias móveis suavizam a curva de temperatura (útil para ver
        # tendência sem o ruído dia a dia). groupby("cidade") garante que a
        # janela de 3/7 dias não misture dados de cidades diferentes;
        # min_periods=1 permite calcular a média mesmo nos primeiros dias,
        # quando ainda não há 3 (ou 7) dias anteriores disponíveis.
        diario["media_movel_3d"] = diario.groupby("cidade")["temp_media"].transform(
            lambda s: s.rolling(window=3, min_periods=1).mean()
        )
        diario["media_movel_7d"] = diario.groupby("cidade")["temp_media"].transform(
            lambda s: s.rolling(window=7, min_periods=1).mean()
        )

        # Em cada dia, qual a posição da cidade no ranking de temperatura
        # (1 = cidade mais quente naquele dia)? groupby("data") compara
        # cidades entre si dentro do mesmo dia; ascending=False faz o maior
        # valor virar o rank 1.
        diario["ranking_temp_dia"] = diario.groupby("data")["temp_media"].rank(
            ascending=False, method="min"
        ).astype(int)

        # apply(..., axis=1) roda a função uma vez por linha (row), porque o
        # cálculo do índice de conforto depende de duas colunas da mesma
        # linha (temp_media e umidade_media) ao mesmo tempo.
        diario["indice_conforto_c"] = diario.apply(_calcular_indice_conforto, axis=1)

        return diario
