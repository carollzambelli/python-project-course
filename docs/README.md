# Documentação (Sphinx)

Esta pasta contém a documentação técnica do projeto, gerada com
[Sphinx](https://www.sphinx-doc.org/) a partir das docstrings de
[`src/clima_pipeline`](../src/clima_pipeline/). O HTML já construído fica em
`docs/_build/html/` — abra `docs/_build/html/index.html` no navegador para ver
o resultado sem precisar rodar nada.

## Sumário

- [O que é o Sphinx e por quê](#o-que-é-o-sphinx-e-por-quê)
- [Conceitos-chave](#conceitos-chave)
  - [reStructuredText (`.rst`)](#restructuredtext-rst)
  - [`autodoc`: docstring vira documentação](#autodoc-docstring-vira-documentação)
  - [`toctree`: a árvore de navegação](#toctree-a-árvore-de-navegação)
  - [Temas](#temas)
  - [Outras extensões usadas](#outras-extensões-usadas)
- [Estrutura desta pasta](#estrutura-desta-pasta)
- [Como instalar](#como-instalar)
- [Como buildar](#como-buildar)
- [Como visualizar](#como-visualizar)
- [Como estender](#como-estender)
- [Troubleshooting](#troubleshooting)
- [Referências](#referências)

## O que é o Sphinx e por quê

[Sphinx](https://www.sphinx-doc.org/) é o gerador de documentação mais usado
no ecossistema Python — é a ferramenta por trás da documentação oficial do
próprio Python, do Django, do NumPy/pandas, do SQLAlchemy etc. A ideia central
é: **a documentação vive junto do código, como docstrings**, e o Sphinx lê
esse código-fonte e monta um site (HTML, mas também PDF/ePub/man pages) com
navegação, busca e referências cruzadas — sem que ninguém precise manter um
documento separado sincronizado manualmente com o código.

Alternativas existem ([MkDocs](https://www.mkdocs.org/) +
[mkdocstrings](https://mkdocstrings.github.io/),
[pdoc](https://pdoc.dev/)), mas o Sphinx é a escolha padrão quando se quer
`autodoc` maduro (extrair documentação de classes/funções automaticamente),
suporte a múltiplos formatos de saída e integração com `intersphinx` (linkar
para a documentação de outras bibliotecas, como pandas e SQLAlchemy, feito
neste projeto — veja `intersphinx_mapping` em [`conf.py`](conf.py)).

## Conceitos-chave

### reStructuredText (`.rst`)

Sphinx usa por padrão [reStructuredText](https://docutils.sourceforge.io/rst.html)
(`.rst`) como formato de marcação — similar ao Markdown, mas com uma sintaxe
mais expressiva para documentação técnica (diretivas, referências cruzadas
automáticas, numeração de seções). Um título em `.rst` é sublinhado com
símbolos repetidos (a hierarquia é definida pela ordem em que os símbolos
aparecem no documento, não por um símbolo fixo por nível):

```rst
Título principal
==================

Subtítulo
-----------
```

Cada arquivo `.rst` desta pasta segue esse padrão — veja
[`index.rst`](index.rst) e os arquivos em [`api/`](api/).

> **Nota:** é possível usar Markdown no lugar de `.rst` instalando
> [MyST-Parser](https://myst-parser.readthedocs.io/), mas este projeto usa
> `.rst` puro por ser a integração mais direta com `autodoc`.

### `autodoc`: docstring vira documentação

A extensão [`sphinx.ext.autodoc`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html)
(habilitada em [`conf.py`](conf.py)) é o motor por trás desta documentação:
ela **importa** o módulo Python de verdade e extrai, via introspecção,
classes, métodos, funções e suas docstrings/assinaturas — não faz parsing de
texto, executa o código de fato. A diretiva usada em cada arquivo `api/*.rst`
é:

```rst
.. automodule:: clima_pipeline.load.sqlite_repository
```

Com `autodoc_default_options` configurado em `conf.py` (`members`,
`undoc-members`, `show-inheritance`), isso já documenta **todas** as classes e
funções públicas do módulo, incluindo assinatura e tipos (via
`autodoc_typehints = "description"`, que transforma type hints do código em
texto legível na doc, sem duplicar informação manualmente).

Como `autodoc` importa o módulo de verdade, o pacote precisa estar instalado
no ambiente onde o build roda (`pip install -e .`) — é por isso que
`clima_pipeline/dashboard/app.py` **não** é documentado via `automodule`
(veja [`api/dashboard.rst`](api/dashboard.rst)): é um script Streamlit cujo
corpo inteiro roda ao ser importado, incluindo chamadas HTTP à API — importar
esse arquivo fora do runtime do `streamlit run` tentaria de fato contatar a
API e falharia. Nesses casos (scripts de entrada, não bibliotecas), documenta-se
em prosa em vez de `automodule`.

A extensão [`sphinx.ext.napoleon`](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
também está habilitada — ela ensina o `autodoc` a entender docstrings em
estilo Google/NumPy (seções `Args:`/`Returns:`), embora as docstrings deste
projeto sejam em prosa livre (ver [`src/README.md`](../src/README.md)); manter
Napoleon ligado não atrapalha e permite adotar esse estilo em módulos futuros
sem reconfigurar nada.

### `toctree`: a árvore de navegação

Diferente do Markdown, arquivos `.rst` não se conectam automaticamente — a
navegação (menu lateral, "próximo"/"anterior") vem da diretiva `toctree`
("table of contents tree"), que lista explicitamente os documentos filhos:

```rst
.. toctree::
   :maxdepth: 2

   api/index
```

[`index.rst`](index.rst) é a raiz dessa árvore; ele aponta para
[`api/index.rst`](api/index.rst), que por sua vez lista cada módulo
documentado (`config`, `pipeline`, `extract`, etc.).

### Temas

O tema controla a aparência do HTML gerado. Este projeto usa
[`sphinx_rtd_theme`](https://sphinx-rtd-theme.readthedocs.io/) (o mesmo visual
do Read the Docs — menu lateral recolhível, busca embutida), configurado em
`conf.py` via `html_theme = "sphinx_rtd_theme"`. Outras opções populares:
`alabaster` (tema padrão do Sphinx, minimalista) e
[`furo`](https://pradyunsg.me/furo/) (mais moderno, com dark mode nativo).

### Outras extensões usadas

- `sphinx.ext.viewcode` — adiciona um link "[código-fonte]" em cada
  classe/função documentada, que mostra o código Python real destacado.
- `sphinx.ext.intersphinx` — permite que um termo como `DataFrame` (usado em
  type hints) vire um link direto para a documentação oficial do pandas, sem
  precisar escrever a URL manualmente.
- `sphinx.ext.autosummary` — gera tabelas-resumo (nome + primeira linha da
  docstring) automaticamente.

## Estrutura desta pasta

```
docs/
├── conf.py          # configuração do Sphinx (tema, extensões, autodoc)
├── index.rst         # página inicial da documentação
├── api/
│   ├── index.rst      # toctree da referência de código
│   ├── config.rst      # automodule: clima_pipeline.config
│   ├── logging_config.rst
│   ├── pipeline.rst
│   ├── extract.rst
│   ├── transform.rst   # cleaner.py + aggregator.py
│   ├── load.rst
│   ├── api.rst          # schemas.py + main.py (FastAPI)
│   └── dashboard.rst    # prosa (não automodule) — ver seção autodoc acima
├── Makefile / make.bat  # atalhos de build (make html)
├── _static/              # assets customizados (CSS/imagens), vazio por padrão
├── _templates/           # templates HTML customizados, vazio por padrão
└── _build/               # saída gerada (HTML) — pode ser apagada e recriada
```

## Como instalar

As dependências de build da documentação ficam no extra `docs` de
[`pyproject.toml`](../pyproject.toml):

```bash
pip install -e ".[docs]"
```

Isso instala `sphinx` e `sphinx-rtd-theme`. Como o `autodoc` importa
`clima_pipeline` de verdade, as dependências normais do projeto também
precisam estar instaladas (`pip install -e .` já cobre isso).

## Como buildar

```bash
cd docs
make html          # equivalente a: sphinx-build -b html . _build/html
```

Sem `make` (ex.: Windows sem Make instalado), rode o `make.bat` ou o
`sphinx-build` direto:

```bash
sphinx-build -b html docs docs/_build/html
```

Para pegar erros de referência/sintaxe como se fossem falhas de build
(recomendado antes de publicar):

```bash
sphinx-build -b html -W docs docs/_build/html
```

## Como visualizar

Abra `docs/_build/html/index.html` diretamente no navegador, ou sirva com um
servidor HTTP simples (necessário se algum recurso usar caminho absoluto):

```bash
python3 -m http.server --directory docs/_build/html 8080
```

Depois acesse `http://localhost:8080`.

## Como estender

- **Novo módulo em `src/clima_pipeline`**: crie um `docs/api/<nome>.rst` com
  `.. automodule:: clima_pipeline.<caminho.do.modulo>` e adicione o nome do
  arquivo (sem `.rst`) ao `toctree` de [`api/index.rst`](api/index.rst).
- **Nova docstring**: nada a fazer na documentação — rode `make html` de novo
  e o `autodoc` já reflete a mudança (ele lê o código no momento do build).
- **Mudar o tema/aparência**: edite `html_theme`/`html_theme_options` em
  [`conf.py`](conf.py).
- **Adicionar uma página de texto livre** (tutorial, guia): crie um `.rst`
  (ou `.md`, adicionando [`myst-parser`](https://myst-parser.readthedocs.io/)
  às extensões) e referencie-o em um `toctree`.

## Troubleshooting

- **`ModuleNotFoundError` durante o build**: o `autodoc` não conseguiu
  importar `clima_pipeline` ou uma de suas dependências — rode
  `pip install -e ".[docs]"` no mesmo ambiente/venv usado para o build.
- **Classe/função não aparece na doc**: confira se o módulo está listado em
  algum `automodule` e se o `toctree` de `api/index.rst` inclui esse arquivo.
  Nomes prefixados com `_` (privados) só aparecem com `undoc-members`/opção
  explícita — já habilitado por padrão neste projeto.
- **Build "successful" mas com avisos (`WARNING`)**: normalmente é referência
  cruzada quebrada (`toctree` apontando para arquivo inexistente) ou
  duplicidade de título — o próprio texto do warning indica o arquivo/linha.

## Referências

- [Documentação oficial do Sphinx](https://www.sphinx-doc.org/en/master/)
- [Guia de reStructuredText do Sphinx](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [`sphinx.ext.autodoc`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html)
- [`sphinx.ext.napoleon`](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
- [`sphinx.ext.intersphinx`](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html)
- [Read the Docs Sphinx Theme](https://sphinx-rtd-theme.readthedocs.io/)
- [Tutorial oficial "Sphinx quickstart"](https://www.sphinx-doc.org/en/master/tutorial/index.html)
