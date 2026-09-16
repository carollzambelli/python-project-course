"""Orquestra extração -> tratamento -> agregação -> persistência."""

import argparse
import json
import logging

import pandas as pd
import requests

from clima_pipeline.config import CIDADES, DATA_FIM_PADRAO, DATA_INICIO_PADRAO, RAW_DIR
from clima_pipeline.extract import OpenMeteoClient
from clima_pipeline.load import SQLiteRepository
from clima_pipeline.transform import ClimaAggregator, ClimaCleaner

# Só de importar clima_pipeline.config acima, o logging já fica configurado
# (veja o logging.basicConfig no fim de config.py) — cada módulo só precisa
# pegar o seu próprio logger, nomeado com __name__ para aparecer nas
# mensagens quem/o quê logou.
logger = logging.getLogger(__name__)


class ClimaPipeline:
    """Orquestra extração -> tratamento -> agregação -> persistência.

    Esta classe não sabe COMO extrair, limpar, agregar ou salvar — ela só
    conhece a ORDEM em que essas etapas acontecem e passa o resultado de uma
    para a próxima. Cada etapa em si vive em sua própria classe
    (OpenMeteoClient, ClimaCleaner, ClimaAggregator, SQLiteRepository).
    """

    def __init__(
        self,
        client: OpenMeteoClient | None = None,
        cleaner: ClimaCleaner | None = None,
        aggregator: ClimaAggregator | None = None,
        repository: SQLiteRepository | None = None,
    ):
        # Cada parâmetro é opcional: se não for passado, cria a implementação
        # real por padrão. Isso é "injeção de dependência" — permite, por
        # exemplo, passar um cleaner "falso" em testes sem precisar mudar o
        # código de ClimaPipeline.
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
        """Roda o pipeline completo para a lista de cidades e o período informados."""
        logger.info("Iniciando pipeline para %d cidade(s): %s", len(cities), cities)

        # Etapa 1 (extração + limpeza): para cada cidade, busca o histórico
        # bruto na API, guarda uma cópia em disco (auditoria/depuração) e já
        # limpa o resultado — um DataFrame horário por cidade, acumulados
        # nesta lista.
        #
        # A busca na API (fetch_historical) é a única parte deste laço que
        # pode falhar por motivo alheio ao nosso código (rede instável,
        # timeout, API fora do ar por um instante). Por isso ela fica dentro
        # de um try/except específico: se UMA cidade falhar, avisamos e
        # seguimos para as próximas, em vez de perder o processamento de
        # todas as outras cidades por causa de uma falha pontual.
        dataframes_horarios = []
        for city in cities:
            try:
                raw = self.client.fetch_historical(city, start, end)
            except requests.RequestException as erro:
                logger.warning("Falha ao buscar clima de '%s': %s (cidade pulada)", city, erro)
                continue
            self._salvar_json_bruto(raw, city)
            dataframes_horarios.append(self.cleaner.clean(raw, city))

        if not dataframes_horarios:
            logger.warning("Nenhuma cidade processada com sucesso; pipeline encerrado sem gravar dados.")
            return

        # Junta os DataFrames das cidades que deram certo num só antes de
        # seguir — ignore_index=True refaz o índice (0, 1, 2, ...) em vez de
        # repetir os índices de cada DataFrame original.
        df_horario = pd.concat(dataframes_horarios, ignore_index=True)
        self.repository.save_raw(df_horario)

        # Etapa 2 (agregação + persistência): a partir do dado horário já
        # salvo, calcula a visão diária (médias, categorias, etc.) e grava
        # também.
        df_diario = self.aggregator.build_daily_view(df_horario)
        self.repository.save_daily(df_diario)

        logger.info(
            "Pipeline concluído: %d linha(s) horária(s), %d linha(s) diária(s)",
            len(df_horario),
            len(df_diario),
        )

    def _salvar_json_bruto(self, raw: dict, city: str) -> None:
        """Salva o JSON exatamente como a API devolveu, antes de qualquer tratamento.

        Serve como backup/auditoria: se um bug for encontrado na limpeza
        depois, dá para reprocessar a partir do dado original sem precisar
        chamar a API de novo.
        """
        caminho = RAW_DIR / f"clima_raw_{city}.json"
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        logger.debug("JSON bruto salvo em %s", caminho)


def _parse_args() -> argparse.Namespace:
    """Define e lê os argumentos de linha de comando (--cidades, --inicio, --fim)."""
    parser = argparse.ArgumentParser(description="Roda o pipeline de dados climáticos.")
    parser.add_argument(
        "--cidades",
        nargs="+",  # aceita um ou mais valores: --cidades sao_paulo recife
        default=list(CIDADES),  # sem o argumento, processa todas as cidades cadastradas
        choices=list(CIDADES),  # argparse já valida e recusa slugs desconhecidos
        help="Slugs das cidades a processar (padrão: todas em config.CIDADES).",
    )
    parser.add_argument("--inicio", default=DATA_INICIO_PADRAO, help="Data inicial (YYYY-MM-DD).")
    parser.add_argument("--fim", default=DATA_FIM_PADRAO, help="Data final (YYYY-MM-DD).")
    return parser.parse_args()


def main() -> None:
    """Ponto de entrada do `python -m clima_pipeline.pipeline`."""
    args = _parse_args()
    ClimaPipeline().run(cities=args.cidades, start=args.inicio, end=args.fim)


if __name__ == "__main__":
    # Só roda main() quando o arquivo é executado diretamente (via
    # `python -m clima_pipeline.pipeline`), não quando é apenas importado
    # por outro módulo (ex.: em testes).
    main()
