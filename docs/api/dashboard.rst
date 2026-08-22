``dashboard`` — Streamlit
============================

``clima_pipeline/dashboard/app.py`` **não** é documentado via ``automodule``:
é um script de entrada do Streamlit — todo o corpo do arquivo roda de cima a
baixo a cada refresh da página (chamadas como ``st.title(...)`` e requisições
HTTP à REST API acontecem em nível de módulo). Importar esse arquivo fora do
runtime do Streamlit (como o ``autodoc`` faria) tentaria abrir a interface e
falhar ao contatar a API, então ele é descrito aqui em prosa.

Funções internas relevantes (definidas no módulo, mas só fazem sentido dentro
do ciclo de execução do Streamlit):

``carregar_cidades(base_url)``
   Busca ``GET /cidades`` na REST API e devolve um ``DataFrame`` de cidades
   disponíveis. Cacheada por 300s via ``st.cache_data``.

``carregar_diario(base_url, slug, inicio, fim)``
   Busca ``GET /clima/diario`` para uma cidade e período. Cacheada por 60s.

``carregar_comparativo(base_url, slugs, variavel)``
   Busca ``GET /clima/comparativo`` para múltiplas cidades e uma variável
   numérica, devolvendo um ``DataFrame`` pivotado (índice = data, colunas =
   cidade). Cacheada por 60s.

Como rodar: veja a seção "Rodando o dashboard" no
`README do projeto <../../README.md>`_.
