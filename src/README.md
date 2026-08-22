# Boas práticas de Python usadas neste pacote

Guia de referência para quem for ler ou estender
[`clima_pipeline/`](clima_pipeline/). Todo exemplo aqui aponta para código real
do pacote — não é teoria solta.

## Sumário

- [PEP 8 e estilo de código](#pep-8-e-estilo-de-código)
- [Documentação de código (docstrings e type hints)](#documentação-de-código-docstrings-e-type-hints)
- [Logging](#logging)
- [Debug com VSCode](#debug-com-vscode)

## PEP 8 e estilo de código

[PEP 8](https://peps.python.org/pep-0008/) é o guia de estilo oficial do
Python — convenções de nomenclatura, espaçamento e organização que tornam
código de qualquer autor previsível de ler. Pontos que aparecem neste pacote:

- **Nomenclatura**: `snake_case` para funções/variáveis/módulos
  (`resolver_slug_cidade`, `open_meteo_client.py`), `PascalCase` para classes
  (`ClimaPipeline`, `SQLiteRepository`, `OpenMeteoClient`), `UPPER_CASE` para
  constantes de módulo (`CIDADES`, `DB_PATH`, `LOG_LEVEL` em
  [`config.py`](clima_pipeline/config.py)). Nomes prefixados com `_` (`_upsert`,
  `_tratar_outliers`, `_CONFIGURADO`) sinalizam "uso interno do módulo/classe" —
  uma convenção, não uma trava real do interpretador.
- **Imports organizados**: biblioteca padrão primeiro, depois bibliotecas de
  terceiros, depois módulos do próprio pacote — veja o topo de
  [`pipeline.py`](clima_pipeline/pipeline.py) (`argparse`/`json`/`logging` →
  `pandas` → `clima_pipeline.*`).
- **Uma responsabilidade por módulo/classe**: `extract/` só fala com a API,
  `transform/` só limpa e agrega, `load/` só persiste, `api/` só expõe HTTP —
  isso é o princípio de responsabilidade única (parte da filosofia por trás do
  PEP 8, embora não seja regra de estilo em si).
- **Comprimento de linha**: PEP 8 recomenda até 79 colunas; times modernos
  costumam relaxar para 88–100 (linha adotada implicitamente neste projeto).
  O importante é **consistência** — configure um formatador (veja abaixo) em
  vez de policiar isso manualmente.
- **Automatize, não policie visualmente**: formatadores como
  [`black`](https://black.readthedocs.io/) e linters como
  [`ruff`](https://docs.astral.sh/ruff/) aplicam/checam PEP 8 automaticamente.
  Sugestão de uso local:
  ```bash
  pip install ruff black
  ruff check src/
  black src/
  ```

## Documentação de código (docstrings e type hints)

### Docstrings

Toda docstring neste pacote segue o mesmo padrão: **primeira linha resume o
que o objeto faz**; parágrafos seguintes (quando existem) explicam contratos
não óbvios — parâmetros especiais, exceções lançadas, efeitos colaterais.

```python
def fetch_historical(self, city: str, start: str, end: str) -> dict:
    """Busca o histórico horário de uma cidade cadastrada em `config.CIDADES`.

    `city` é o slug da cidade (ex.: "sao_paulo"). Lança `KeyError` se o slug
    não estiver cadastrado e `requests.HTTPError` se a API responder com erro.
    """
```
([`extract/open_meteo_client.py`](clima_pipeline/extract/open_meteo_client.py))

Note o que a docstring **não** faz: não repete o que já está óbvio pela
assinatura (`city: str, start: str, end: str) -> dict` já diz "recebe três
strings, devolve um dict") — ela documenta o que só está na cabeça de quem
escreveu: qual o formato esperado de `city` e quais exceções esperar.

Regra prática adotada no pacote: **docstring de uma linha quando o nome da
função já é autoexplicativo** (ex. `close(self) -> None`, sem docstring, pois
"fecha a sessão" não precisa de explicação), e docstring com contexto extra
apenas quando há uma pegadinha real (formato de entrada, exceção lançada,
efeito colateral).

Convenções de formatação de docstring mais usadas na comunidade (não usadas
literalmente aqui, mas úteis para projetos maiores/com docs geradas via
Sphinx):

- [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) — `Args:`, `Returns:`, `Raises:`.
- [NumPy style](https://numpydoc.readthedocs.io/en/latest/format.html) — seções com `----------` sublinhadas.
- [reStructuredText/Sphinx](https://www.sphinx-doc.org/en/master/usage/domains/python.html) — `:param nome:`, `:returns:`, `:raises:`.

Este projeto usa docstrings **em prosa livre** (sem seções estruturadas) por
serem pequenas o suficiente para isso; veja [`docs/README.md`](../docs/README.md)
para como o Sphinx extrai e renderiza essas docstrings automaticamente via
`autodoc`, independente do estilo escolhido.

### Type hints

Todo o pacote usa [type hints](https://docs.python.org/3/library/typing.html)
nas assinaturas — não é imposto pelo interpretador (Python não vira uma
linguagem estaticamente tipada por isso), mas ajuda o VSCode/Pylance a
autocompletar e pegar erros antes de rodar:

```python
def resolver_slug_cidade(identificador: str) -> str | None:
```
([`config.py`](clima_pipeline/config.py)) — a assinatura já documenta que a
função pode devolver `None` (cidade não encontrada), então quem chama sabe que
precisa tratar esse caso.

```python
def __init__(
    self,
    client: OpenMeteoClient | None = None,
    cleaner: ClimaCleaner | None = None,
    ...
)
```
([`pipeline.py`](clima_pipeline/pipeline.py)) — o padrão `Tipo | None = None`
é **injeção de dependência opcional**: em produção usa a implementação real
por padrão, em teste passa-se um dublê (mock/fake).

Para checar tipos de fato (além do que o editor sinaliza), rode
[`mypy`](https://mypy-lang.org/) ou [`pyright`](https://microsoft.github.io/pyright/):
```bash
pip install mypy
mypy src/clima_pipeline
```

## Logging

**Nunca** use `print()` para diagnóstico em código de produção — não dá para
filtrar por severidade, não tem timestamp, não vai para arquivo, não pode ser
desligado seletivamente. Este pacote centraliza logging em
[`logging_config.py`](clima_pipeline/logging_config.py):

```python
def setup_logging(level: str | None = None) -> None:
    """Configura o logger raiz uma única vez (chamadas repetidas são no-op)."""
    ...
    logging.basicConfig(level=nivel, handlers=[console_handler, arquivo_handler])
```

Pontos importantes desse design:

- **Configuração central, uso descentralizado**: `setup_logging()` é chamado
  uma única vez (no `main()` do pipeline, no `lifespan` da API) — cada módulo
  só faz `logger = logging.getLogger(__name__)` no topo e usa `logger.info(...)`,
  `logger.warning(...)`, etc. Usar `__name__` faz o log já vir identificado com
  o módulo de origem (`clima_pipeline.transform.cleaner`, por exemplo).
- **Dois destinos (handlers)**: console (para acompanhar em tempo real) e
  arquivo rotativo (`RotatingFileHandler`, `logs/pipeline.log`, até 3 arquivos
  de 1MB) — para investigar depois sem lotar o disco.
- **Níveis de severidade**, do menos ao mais grave:
  `DEBUG` < `INFO` < `WARNING` < `ERROR` < `CRITICAL`. Uso no pacote:
  - `logger.debug(...)` — detalhe só relevante para depuração fina (ex.: "JSON
    bruto salvo em %s" em `pipeline.py`).
  - `logger.info(...)` — marcos normais de execução ("Pipeline concluído: %d
    linha(s)...").
  - `logger.warning(...)` — algo inesperado mas recuperável (linhas
    duplicadas removidas, outliers corrigidos em `cleaner.py`).
  - (o pacote não usa `error`/`critical` hoje porque falhas reais viram
    exceção — não faz sentido logar e continuar quando o dado está
    comprometido.)
- **Nunca formate a mensagem com f-string** (`logger.info(f"...{x}")`) — use
  `%s`/`%d` com argumentos posicionais (`logger.info("...%s", x)`). A
  f-string é sempre avaliada mesmo se o nível de log estiver desligado; o
  `%s` só formata se a mensagem for realmente emitida.
- **Configuração via ambiente**: `CLIMA_LOG_LEVEL` (ver
  [`.env.example`](../.env.example)) muda o nível sem precisar editar código —
  útil para ligar `DEBUG` temporariamente em produção.

## Debug com VSCode

Prefira o depurador do VSCode a `print()`s espalhados pelo código — ele para a
execução, deixa inspecionar variáveis e rodar código no ponto exato do erro.

1. **Breakpoints**: clique à esquerda do número da linha (ou `F9`) no arquivo
   que quer investigar — por exemplo, dentro de
   [`transform/cleaner.py`](clima_pipeline/transform/cleaner.py), na linha do
   `_tratar_outliers`.
2. **Rodar com o debugger** (não "Run Python File" — use "Run and Debug",
   ícone de inseto na barra lateral, ou `F5`). Para um módulo específico do
   pacote (em vez de um script solto), crie/edite `.vscode/launch.json`:
   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "name": "Pipeline (debug)",
         "type": "debugpy",
         "request": "launch",
         "module": "clima_pipeline.pipeline",
         "args": ["--cidades", "sao_paulo", "--inicio", "2025-01-01", "--fim", "2025-01-05"],
         "console": "integratedTerminal"
       },
       {
         "name": "API (debug)",
         "type": "debugpy",
         "request": "launch",
         "module": "uvicorn",
         "args": ["clima_pipeline.api.main:app", "--reload"],
         "console": "integratedTerminal"
       }
     ]
   }
   ```
3. **Na pausa**: use os painéis *Variables* (estado local), *Watch* (expressões
   customizadas, ex. `df.shape`), *Call Stack* (quem chamou quem) e o
   **Debug Console** (executa código Python arbitrário no contexto da pausa —
   ótimo para inspecionar um `pd.DataFrame` sem precisar de `print`).
4. **Controles de execução**: *Continue* (`F5`), *Step Over* (`F10`, executa a
   linha sem entrar em funções chamadas), *Step Into* (`F11`, entra na função
   chamada — útil para ver o que `self.aggregator.build_daily_view(df)` faz por
   dentro), *Step Out* (`Shift+F11`).
5. **Breakpoint condicional**: clique direito no breakpoint → *Edit
   Breakpoint* → condição, ex. `city == "manaus"` — pausa só quando a condição
   é verdadeira, essencial ao depurar um loop sobre `CIDADES`.
6. **Notebooks**: a extensão Jupyter do VSCode também suporta breakpoints
   dentro de células `.ipynb` — mesmo fluxo, aplicado a
   [`notebooks/`](../notebooks/).

Documentação oficial: [Debugging Python in VSCode](https://code.visualstudio.com/docs/python/debugging).
