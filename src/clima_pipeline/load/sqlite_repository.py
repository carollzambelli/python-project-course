"""Persistência em SQLite via SQLAlchemy Core: schema, upsert e leitura."""

import logging

import pandas as pd
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, create_engine, select
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

from clima_pipeline.config import DB_PATH

logger = logging.getLogger(__name__)

_COLUNAS_RAW = ["cidade", "datetime", "temp_c", "umidade_pct", "precipitacao_mm", "vento_kmh"]
_COLUNAS_DIARIO = [
    "cidade", "data", "temp_media", "temp_min", "temp_max", "umidade_media",
    "precipitacao_total", "vento_medio", "categoria_temp", "categoria_chuva",
    "media_movel_3d", "media_movel_7d", "ranking_temp_dia", "indice_conforto_c",
]


class SQLiteRepository:
    """Responsável apenas por persistência."""

    def __init__(self, db_path=DB_PATH):
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.metadata = MetaData()
        self._clima_raw = self._tabela_raw()
        self._clima_diario = self._tabela_diario()
        self.metadata.create_all(self.engine, checkfirst=True)

    def _tabela_raw(self) -> Table:
        return Table(
            "clima_raw",
            self.metadata,
            Column("cidade", String, primary_key=True),
            Column("datetime", String, primary_key=True),
            Column("temp_c", Float),
            Column("umidade_pct", Float),
            Column("precipitacao_mm", Float),
            Column("vento_kmh", Float),
        )

    def _tabela_diario(self) -> Table:
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
        if df.empty:
            return

        registros = df.to_dict(orient="records")
        stmt = sqlite_upsert(tabela).values(registros)
        colunas_atualizaveis = [c.name for c in tabela.columns if c.name not in colunas_pk]
        stmt = stmt.on_conflict_do_update(
            index_elements=colunas_pk,
            set_={c: getattr(stmt.excluded, c) for c in colunas_atualizaveis},
        )

        with self.engine.begin() as conn:
            conn.execute(stmt)

        logger.info("Upsert em '%s': %d linha(s)", tabela.name, len(registros))

    def save_raw(self, df: pd.DataFrame) -> None:
        df = df[_COLUNAS_RAW].assign(datetime=lambda d: d["datetime"].astype(str))
        self._upsert(self._clima_raw, df, colunas_pk=["cidade", "datetime"])

    def save_daily(self, df: pd.DataFrame) -> None:
        df = df[_COLUNAS_DIARIO].assign(data=lambda d: d["data"].astype(str))
        self._upsert(self._clima_diario, df, colunas_pk=["cidade", "data"])

    def get_raw(self, city: str | None = None) -> pd.DataFrame:
        query = select(self._clima_raw)
        if city:
            query = query.where(self._clima_raw.c.cidade == city)
        return pd.read_sql(query, self.engine, parse_dates=["datetime"])

    def get_daily(self, city: str | None = None) -> pd.DataFrame:
        query = select(self._clima_diario)
        if city:
            query = query.where(self._clima_diario.c.cidade == city)
        return pd.read_sql(query, self.engine, parse_dates=["data"])

    def get_cidades_disponiveis(self) -> list[str]:
        query = select(self._clima_diario.c.cidade).distinct()
        with self.engine.connect() as conn:
            return sorted(row[0] for row in conn.execute(query))

    def dispose(self) -> None:
        self.engine.dispose()
