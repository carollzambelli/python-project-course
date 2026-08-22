"""REST API (FastAPI) para consultar o clima persistido em SQLite."""

import datetime as dt
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse

from clima_pipeline.api.schemas import CidadeOut, ClimaDiarioOut, HealthOut
from clima_pipeline.config import CIDADES, resolver_slug_cidade
from clima_pipeline.load import SQLiteRepository
from clima_pipeline.logging_config import setup_logging
from clima_pipeline.transform import ClimaAggregator


@lru_cache
def get_repository() -> SQLiteRepository:
    return SQLiteRepository()


@lru_cache
def get_aggregator() -> ClimaAggregator:
    return ClimaAggregator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield
    get_repository().dispose()


app = FastAPI(
    title="Clima Pipeline API",
    description="Consulta dados climáticos históricos tratados e agregados.",
    version="0.1.0",
    lifespan=lifespan,
)


def _resolver_ou_404(identificador: str) -> str:
    slug = resolver_slug_cidade(identificador)
    if slug is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cidade '{identificador}' não encontrada. Use /cidades para ver as opções.",
        )
    return slug


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut()


@app.get("/cidades", response_model=list[CidadeOut])
def listar_cidades() -> list[CidadeOut]:
    return [
        CidadeOut(slug=slug, nome_exibicao=info["nome_exibicao"], uf=info["uf"],
                   regiao=info["regiao"], lat=info["lat"], lon=info["lon"])
        for slug, info in CIDADES.items()
    ]


@app.get("/clima/diario", response_model=list[ClimaDiarioOut])
def clima_diario(
    cidade: str = Query(..., description="Slug, nome de exibição ou UF da cidade"),
    inicio: dt.date | None = Query(None, description="Data inicial (YYYY-MM-DD)"),
    fim: dt.date | None = Query(None, description="Data final (YYYY-MM-DD)"),
) -> list[ClimaDiarioOut]:
    slug = _resolver_ou_404(cidade)
    df = get_repository().get_daily(city=slug)

    if df.empty:
        return []

    df["data"] = df["data"].dt.date
    if inicio:
        df = df[df["data"] >= inicio]
    if fim:
        df = df[df["data"] <= fim]

    return [ClimaDiarioOut(**row) for row in df.to_dict(orient="records")]


@app.get("/clima/comparativo")
def clima_comparativo(
    cidades: str = Query(..., description="Slugs/UFs/nomes separados por vírgula, ex.: SP,RJ"),
    variavel: str = Query("temp_media", description="Coluna numérica de clima_diario a comparar"),
) -> dict:
    slugs = [_resolver_ou_404(c) for c in cidades.split(",")]

    repositorio = get_repository()
    df = pd_concat_diarios(repositorio, slugs)
    if df.empty:
        return {"variavel": variavel, "registros": []}

    pivot = get_aggregator().build_pivot(df, valor=variavel)
    pivot = pivot.rename(columns={slug: CIDADES[slug]["nome_exibicao"] for slug in pivot.columns})
    pivot.index = pivot.index.astype(str)

    registros = pivot.reset_index().rename(columns={"index": "data"}).to_dict(orient="records")
    return {"variavel": variavel, "registros": registros}


def pd_concat_diarios(repositorio: SQLiteRepository, slugs: list[str]):
    import pandas as pd

    partes = [repositorio.get_daily(city=slug) for slug in slugs]
    partes = [p for p in partes if not p.empty]
    if not partes:
        return pd.DataFrame()

    df = pd.concat(partes, ignore_index=True)
    df["data"] = df["data"].dt.date
    return df
