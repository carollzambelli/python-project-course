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
   Chamada uma vez por cidade selecionada; os resultados são concatenados
   num único ``DataFrame`` (``diario``) usado pelos dois gráficos e pela
   tabela final.

O comparativo entre cidades não faz uma chamada extra à API: é montado a
partir do próprio ``diario`` com ``diario.pivot_table(index="data",
columns="nome_exibicao", values=variavel)`` — a API só expõe o dado por
cidade (``/clima/diario``), e toda comparação/apresentação fica no
dashboard.

Como rodar: veja a seção "Rodando o dashboard" no
`README do projeto <../../README.md>`_.
