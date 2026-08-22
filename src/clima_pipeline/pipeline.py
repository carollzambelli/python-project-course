"""Orquestra extração -> tratamento -> agregação -> persistência."""

import argparse
import json
import logging

import pandas as pd

from clima_pipeline.config import CIDADES, DATA_FIM_PADRAO, DATA_INICIO_PADRAO, RAW_DIR
from clima_pipeline.extract import OpenMeteoClient
from clima_pipeline.load import SQLiteRepository
from clima_pipeline.logging_config import setup_logging
from clima_pipeline.transform import ClimaAggregator, ClimaCleaner

logger = logging.getLogger(__name__)


class ClimaPipeline:
    """Orquestra extração -> tratamento -> agregação -> persistência."""

    def __init__(
        self,
        client: OpenMeteoClient | None = None,
        cleaner: ClimaCleaner | None = None,
        aggregator: ClimaAggregator | None = None,
        repository: SQLiteRepository | None = None,
    ):
        self.client = client or OpenMeteoClient()
        self.cleaner = cleaner or ClimaCleaner()
        self.aggregator = aggregator or ClimaAggregator()
        self.repository = repository or SQLiteRepository()

    def run(
        self,
        cities: list[str],
        start: str = DATA_INICIO_PADRAO,
        end: str = DATA_FIM_PADRAO,
    ) -> None:
        logger.info("Iniciando pipeline para %d cidade(s): %s", len(cities), cities)

        dataframes_horarios = []
        for city in cities:
            raw = self.client.fetch_historical(city, start, end)
            self._salvar_json_bruto(raw, city)
            dataframes_horarios.append(self.cleaner.clean(raw, city))

        df_horario = pd.concat(dataframes_horarios, ignore_index=True)
        self.repository.save_raw(df_horario)

        df_diario = self.aggregator.build_daily_view(df_horario)
        self.repository.save_daily(df_diario)

        logger.info(
            "Pipeline concluído: %d linha(s) horária(s), %d linha(s) diária(s)",
            len(df_horario),
            len(df_diario),
        )

    def _salvar_json_bruto(self, raw: dict, city: str) -> None:
        caminho = RAW_DIR / f"clima_raw_{city}.json"
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        logger.debug("JSON bruto salvo em %s", caminho)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Roda o pipeline de dados climáticos.")
    parser.add_argument(
        "--cidades",
        nargs="+",
        default=list(CIDADES),
        choices=list(CIDADES),
        help="Slugs das cidades a processar (padrão: todas em config.CIDADES).",
    )
    parser.add_argument("--inicio", default=DATA_INICIO_PADRAO, help="Data inicial (YYYY-MM-DD).")
    parser.add_argument("--fim", default=DATA_FIM_PADRAO, help="Data final (YYYY-MM-DD).")
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = _parse_args()
    ClimaPipeline().run(cities=args.cidades, start=args.inicio, end=args.fim)


if __name__ == "__main__":
    main()
