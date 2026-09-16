# Reexporta OpenMeteoClient para quem importar o pacote (não o módulo)
# possa escrever "from clima_pipeline.extract import OpenMeteoClient" em vez
# do caminho completo "from clima_pipeline.extract.open_meteo_client import
# OpenMeteoClient" — só um atalho de import, não muda o comportamento.
from clima_pipeline.extract.open_meteo_client import OpenMeteoClient

__all__ = ["OpenMeteoClient"]
