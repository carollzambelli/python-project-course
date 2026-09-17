"""Contratos (Pydantic models) da REST API.

Cada classe aqui descreve o formato exato de uma resposta JSON da API — quais
campos existem e de que tipo é cada um. O FastAPI usa essas classes para:
1) validar automaticamente o que os endpoints devolvem (se um campo vier do
   tipo errado, a API acusa erro em vez de mandar um JSON inválido);
2) gerar sozinho a documentação interativa em /docs.
"""

import datetime as dt
from pydantic import BaseModel


class HealthOut(BaseModel):
    """Resposta de GET /health — só confirma que a API está de pé."""

    status: str = "ok"


class CidadeOut(BaseModel):
    """Uma cidade cadastrada, no formato devolvido por GET /cidades."""

    slug: str
    nome_exibicao: str
    uf: str
    regiao: str
    lat: float
    lon: float


class ClimaDiarioOut(BaseModel):
    """Uma linha da visão diária, no formato devolvido por GET /clima/diario.

    Os nomes e tipos aqui espelham exatamente as colunas que
    ClimaAggregator.build_daily_view() calcula e que SQLiteRepository grava
    em 'clima_diario' — é o mesmo dado, só "traduzido" para um contrato de
    API formal.
    """

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
