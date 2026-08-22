"""Contratos (Pydantic models) da REST API."""

import datetime as dt

from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str = "ok"


class CidadeOut(BaseModel):
    slug: str
    nome_exibicao: str
    uf: str
    regiao: str
    lat: float
    lon: float


class ClimaDiarioOut(BaseModel):
    cidade: str
    data: dt.date
    temp_media: float
    temp_min: float
    temp_max: float
    umidade_media: float
    precipitacao_total: float
    vento_medio: float
    categoria_temp: str
    categoria_chuva: str
    media_movel_3d: float
    media_movel_7d: float
    ranking_temp_dia: int
    indice_conforto_c: float
