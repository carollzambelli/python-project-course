"""Persistência em SQLite via SQLAlchemy Core: schema, upsert e leitura."""

import logging

import pandas as pd
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, create_engine, select
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

from clima_pipeline.config import DB_PATH

logger = logging.getLogger(__name__)

# Lista explícita e ordenada das colunas que vão para cada tabela — usada
# para garantir que o DataFrame tenha exatamente essas colunas (nem a mais,
# nem a menos) antes de gravar, e na mesma ordem em que a tabela foi criada.
_COLUNAS_RAW = ["cidade", "datetime", "temp_c", "umidade_pct", "precipitacao_mm", "vento_kmh"]
_COLUNAS_DIARIO = [
    "cidade", "data", "temp_media", "temp_min", "temp_max", "umidade_media",
    "precipitacao_total", "vento_medio", "categoria_temp", "categoria_chuva",
    "media_movel_3d", "media_movel_7d", "ranking_temp_dia", "indice_conforto_c",
]


class SQLiteRepository:
    """Responsável apenas por persistência.

    "Repository" é um padrão comum: o resto do código (pipeline, API) não
    escreve SQL nem conhece a estrutura das tabelas — só chama métodos como
    save_daily(df) ou get_daily(cidade). Se um dia trocarmos SQLite por outro
    banco, só esta classe precisa mudar.
    """

    def __init__(self, db_path=DB_PATH):
        # SQLAlchemy Core: engine é a conexão com o banco (aqui, um arquivo
        # SQLite local); MetaData guarda a definição das tabelas em memória
        # (schema), sem precisar escrever SQL "CREATE TABLE" à mão.
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.metadata = MetaData()
        self._clima_raw = self._tabela_raw()
        self._clima_diario = self._tabela_diario()
        # Cria as tabelas no arquivo .db se ainda não existirem (checkfirst
        # evita erro caso já existam de uma execução anterior).
        self.metadata.create_all(self.engine, checkfirst=True)

    def _tabela_raw(self) -> Table:
        """Schema da tabela com dado horário tratado (uma linha por cidade+hora)."""
        return Table(
            "clima_raw",
            self.metadata,
            # Chave primária composta (cidade, datetime): impede duas linhas
            # para a mesma cidade na mesma hora — e é exatamente o que
            # _upsert() usa para decidir se uma linha é nova ou já existe.
            Column("cidade", String, primary_key=True),
            Column("datetime", String, primary_key=True),
            Column("temp_c", Float),
            Column("umidade_pct", Float),
            Column("precipitacao_mm", Float),
            Column("vento_kmh", Float),
        )

    def _tabela_diario(self) -> Table:
        """Schema da tabela com a visão agregada (uma linha por cidade+dia)."""
        return Table(
            "clima_diario",
            self.metadata,
            Column("cidade", String, primary_key=True),
            Column("data", String, primary_key=True),
            Column("temp_media", Float),
            Column("temp_min", Float),
            Column("temp_max", Float),
            Column("umidade_media", Float),
            Column("precipitacao_total", Float),
            Column("vento_medio", Float),
            Column("categoria_temp", String),
            Column("categoria_chuva", String),
            Column("media_movel_3d", Float),
            Column("media_movel_7d", Float),
            Column("ranking_temp_dia", Integer),
            Column("indice_conforto_c", Float),
        )

    def _upsert(self, tabela: Table, df: pd.DataFrame, colunas_pk: list[str]) -> None:
        """"UPSERT" = INSERT, mas se já existir uma linha com a mesma chave primária, atualiza em vez de duplicar.

        Isso é o que torna seguro rodar o pipeline várias vezes para o mesmo
        período: em vez de acumular linhas repetidas, os dados mais recentes
        simplesmente substituem os antigos.
        """
        if df.empty:
            return

        # to_dict(orient="records") transforma o DataFrame numa lista de
        # dicts — um por linha — que é o formato que o SQLAlchemy espera
        # para inserir vários registros de uma vez.
        registros = df.to_dict(orient="records")
        stmt = sqlite_upsert(tabela).values(registros)
        # "Se colidir com uma chave primária já existente, atualize todas as
        # colunas que NÃO são chave primária com os novos valores" — esse é
        # o dialeto específico do SQLite para UPSERT (ON CONFLICT DO UPDATE).
        colunas_atualizaveis = [c.name for c in tabela.columns if c.name not in colunas_pk]
        stmt = stmt.on_conflict_do_update(
            index_elements=colunas_pk,
            set_={c: getattr(stmt.excluded, c) for c in colunas_atualizaveis},
        )

        # engine.begin() abre uma transação e faz commit automático ao sair
        # do "with" sem erro (ou rollback se algo lançar exceção) — evita
        # deixar a escrita "pela metade" no banco.
        with self.engine.begin() as conn:
            conn.execute(stmt)

        logger.info("Upsert em '%s': %d linha(s)", tabela.name, len(registros))

    def save_raw(self, df: pd.DataFrame) -> None:
        """Grava o DataFrame horário (saída de ClimaCleaner) em 'clima_raw'."""
        # Seleciona só as colunas esperadas (na ordem certa) e converte
        # datetime para string, porque a coluna no SQLite é String, não um
        # tipo de data nativo (SQLite não tem um tipo DATETIME de verdade).
        df = df[_COLUNAS_RAW].assign(datetime=lambda d: d["datetime"].astype(str))
        self._upsert(self._clima_raw, df, colunas_pk=["cidade", "datetime"])

    def save_daily(self, df: pd.DataFrame) -> None:
        """Grava o DataFrame diário (saída de ClimaAggregator) em 'clima_diario'."""
        df = df[_COLUNAS_DIARIO].assign(data=lambda d: d["data"].astype(str))
        self._upsert(self._clima_diario, df, colunas_pk=["cidade", "data"])

    def get_daily(self, city: str | None = None) -> pd.DataFrame:
        """Lê a visão diária do banco; se `city` for informado, filtra só aquela cidade.

        É este método que a API chama a cada requisição (não o pipeline) —
        veja api/main.py.
        """
        query = select(self._clima_diario)
        if city:
            query = query.where(self._clima_diario.c.cidade == city)
        # parse_dates converte a coluna "data" (armazenada como texto) de
        # volta para datetime do pandas ao ler — o inverso do astype(str)
        # feito em save_daily().
        return pd.read_sql(query, self.engine, parse_dates=["data"])

    def dispose(self) -> None:
        """Fecha as conexões do engine. Chamado no encerramento da API (veja api/main.py)."""
        self.engine.dispose()
