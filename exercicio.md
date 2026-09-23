# Trabalho final — melhorando o `clima_pipeline`

## O que você vai fazer

Você vai adicionar **duas funcionalidades** ao projeto que construímos nas aulas:

| # | Funcionalidade | Em uma frase |
|---|----------------|--------------|
| 1 | **Novas cidades e sensação térmica** | Colocar Belém e Curitiba no projeto e trazer um dado novo da API (a sensação térmica) até o dashboard. |
| 2 | **Resumo do período** | Criar um endpoint na API que responde perguntas como "qual foi o dia mais quente?" e mostrar essas respostas no dashboard. |

Faça **na ordem** (primeiro a 1, depois a 2), porque a Funcionalidade 2 usa
o dado criado na Funcionalidade 1.

> 💡 **Dica geral:** quase tudo que você vai escrever já tem um exemplo
> parecido no próprio projeto. Quando travar, procure no código algo que
> faz uma coisa semelhante e use como modelo.

---

## Sumário

- [Parte 0 — Preparando o ambiente](#parte-0--preparando-o-ambiente)
- [Relembrando: como o projeto funciona](#relembrando-como-o-projeto-funciona)
- [Funcionalidade 1 — Novas cidades e sensação térmica](#funcionalidade-1--novas-cidades-e-sensação-térmica)
- [Funcionalidade 2 — Resumo do período](#funcionalidade-2--resumo-do-período)
- [Problemas comuns e como resolver](#problemas-comuns-e-como-resolver)
- [O que entregar](#o-que-entregar)
- [Como o trabalho será avaliado](#como-o-trabalho-será-avaliado)

---

## Parte 0 — Preparando o ambiente

Antes de mudar qualquer coisa, garanta que o projeto **funciona do jeito que
está**. Se algo já estiver quebrado antes de você começar, vai ser muito
difícil saber se o erro é seu ou não.

1. Abra o terminal na pasta do projeto e ative o ambiente virtual:
   ```bash
   source .venv/bin/activate
   ```
   (no Windows: `.venv\Scripts\activate`)
2. Instale o projeto:
   ```bash
   pip install -e .
   ```
3. Rode o pipeline (ele baixa os dados da internet, trata e salva no banco):
   ```bash
   python -m clima_pipeline.pipeline
   ```
   No final deve aparecer uma mensagem parecida com
   `Pipeline concluído: ... linha(s) horária(s), ... linha(s) diária(s)`.
4. Suba a API:
   ```bash
   uvicorn clima_pipeline.api.main:app --reload
   ```
   Abra no navegador: <http://127.0.0.1:8000/docs>. Você deve ver a página
   de documentação da API com os endpoints `/health`, `/cidades` e `/clima/diario`.
5. Em **outro terminal** (deixe a API rodando no primeiro), suba o dashboard:
   ```bash
   streamlit run src/clima_pipeline/dashboard/app.py
   ```
   O navegador abre sozinho com o dashboard.

✅ Se os 5 passos funcionaram, você está pronto para começar.

> 💡 A opção `--reload` faz a API reiniciar sozinha toda vez que você salva
> um arquivo. O Streamlit também percebe mudanças: aparece um botão
> **"Rerun"** no canto superior direito da página.

---

## Relembrando: como o projeto funciona

O dado passa por várias etapas, cada uma em um arquivo diferente:

```
 Open-Meteo (internet)
        │
        ▼
 1. extract/open_meteo_client.py   → baixa o JSON da API
        │
        ▼
 2. transform/cleaner.py           → limpa o dado e cria uma tabela com UMA LINHA POR HORA
        │
        ▼
 3. transform/aggregator.py        → transforma em uma tabela com UMA LINHA POR DIA
        │
        ▼
 4. load/sqlite_repository.py      → salva as duas tabelas no banco (data/clima.db)
        │
        ▼
 5. api/main.py + api/schemas.py   → a API lê do banco e devolve em JSON
        │
        ▼
 6. dashboard/app.py               → o dashboard chama a API e desenha gráficos
```

E o arquivo [`config.py`](src/clima_pipeline/config.py) guarda as configurações
usadas por todos os outros (lista de cidades, variáveis pedidas à API, etc.).

### Como testar um arquivo sozinho

Quase todo arquivo do projeto termina com um bloco assim:

```python
if __name__ == "__main__":
    # dados falsos (mock) para testar este arquivo sozinho
    ...
```

Esse bloco só roda quando você executa o arquivo diretamente. Ele usa
**dados falsos** (inventados) para você testar aquele pedaço do código
**sem precisar da internet nem do banco**. Para rodar, use `python -m` e o
caminho do arquivo com pontos no lugar das barras, sem o `.py`:

```bash
python -m clima_pipeline.config
python -m clima_pipeline.transform.cleaner
python -m clima_pipeline.transform.aggregator
python -m clima_pipeline.load.sqlite_repository
```

Você vai usar muito esses comandos para conferir cada passo.

### Como olhar o que está salvo no banco

Com o programa `sqlite3` (se estiver instalado):

```bash
sqlite3 data/clima.db "SELECT * FROM clima_diario LIMIT 5;"
```

Ou, se não tiver o `sqlite3`, com Python e pandas:

```bash
python -c "import sqlite3, pandas as pd; print(pd.read_sql('SELECT * FROM clima_diario LIMIT 5', sqlite3.connect('data/clima.db')))"
```

---

## Funcionalidade 1 — Novas cidades e sensação térmica

### O que é

Hoje o projeto tem 5 cidades e busca 4 informações na API (temperatura,
umidade, chuva e vento). Nesta funcionalidade você vai:

- **Parte A:** adicionar as cidades de **Belém** e **Curitiba**;
- **Parte B:** buscar uma informação nova na API, a **sensação térmica**
  (a temperatura que a gente "sente" na pele), e fazer ela aparecer no dashboard.

### Por que isso é importante

A Parte B mostra na prática uma coisa muito comum no trabalho com dados:
**uma coluna nova precisa passar por todas as etapas do pipeline**. Se você
esquecer uma etapa, o dado "some" no meio do caminho. Por isso vamos fazer
etapa por etapa, conferindo sempre.

### Antes de começar: faça um backup do banco

O banco atual (`data/clima.db`) foi criado **sem** a coluna de sensação
térmica, e ele **não é atualizado sozinho** quando você cria uma coluna nova
no código. Por isso, antes de começar, **renomeie** estes dois arquivos
(clique com o botão direito → Renomear, no VSCode):

| Arquivo atual | Renomeie para |
|---------------|---------------|
| `data/clima.db` | `data/clima_backup.db` |
| `data/clima_teste.db` | `data/clima_teste_backup.db` |

Quando você rodar o pipeline de novo, um banco novo, já com as colunas novas,
será criado automaticamente.

---

### Parte A — Adicionar Belém e Curitiba

#### Passo A1 — Cadastrar as cidades

📄 Arquivo: [`src/clima_pipeline/config.py`](src/clima_pipeline/config.py)

Procure o dicionário `CIDADES`. Cada cidade é uma entrada com o mesmo
formato. Adicione Belém e Curitiba **no final**, antes do `}` que fecha o
dicionário, seguindo o mesmo formato das outras:

```python
    "recife": {
        "nome_exibicao": "Recife",
        "lat": -8.0476,
        "lon": -34.8770,
        "uf": "PE",
        "regiao": "Nordeste",
    },
    # ↓↓↓ NOVO ↓↓↓
    "belem": {
        "nome_exibicao": "Belém",
        "lat": -1.4558,
        "lon": -48.4902,
        "uf": "PA",
        "regiao": "Norte",
    },
    "curitiba": {
        # complete seguindo o mesmo modelo:
        # nome_exibicao: Curitiba | lat: -25.4284 | lon: -49.2733 | uf: PR | regiao: Sul
    },
}
```

> ⚠️ Cuidado com as **vírgulas**: toda entrada do dicionário termina com `},`.
> Esquecer uma vírgula dá `SyntaxError`.

#### Passo A2 — Conferir

No final do mesmo arquivo, no bloco `if __name__ == "__main__":`, existe a
lista `entradas_mock`. Acrescente algumas entradas das cidades novas:

```python
entradas_mock = ["sao_paulo", "SP", "Rio de Janeiro", "cidade_inexistente", "PA", "Curitiba", "belem"]
```

Rode:

```bash
python -m clima_pipeline.config
```

✅ Resultado esperado (as últimas linhas):

```
PA -> 'belem'
Curitiba -> 'curitiba'
belem -> 'belem'
```

Pronto! Não é preciso mudar mais nada para as cidades novas: o pipeline, a
API e o dashboard leem a lista de cidades a partir de `CIDADES`.

---

### Parte B — Adicionar a sensação térmica

Na API do Open-Meteo, a sensação térmica se chama `apparent_temperature`. No
nosso projeto, vamos chamá-la de:

- `sensacao_c` → na tabela **por hora** (igual a `temp_c`);
- `sensacao_media` e `sensacao_max` → na tabela **por dia** (igual a `temp_media` e `temp_max`).

Vamos seguir o caminho do dado, etapa por etapa.

#### Passo B1 — Pedir a variável nova à API

📄 Arquivo: [`src/clima_pipeline/config.py`](src/clima_pipeline/config.py)

A lista `VARIAVEIS_HORARIAS` diz **quais informações** o projeto pede à API.
Acrescente a nova no final:

```python
VARIAVEIS_HORARIAS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "apparent_temperature",  # NOVO: sensação térmica
]
```

#### Passo B2 — Tratar a coluna na limpeza

📄 Arquivo: [`src/clima_pipeline/transform/cleaner.py`](src/clima_pipeline/transform/cleaner.py)

Aqui são **4 mudanças** no mesmo arquivo.

**1) Renomear a coluna.** O dicionário `_RENOMEIA_COLUNAS` troca os nomes em
inglês da API pelos nossos nomes em português. Acrescente:

```python
_RENOMEIA_COLUNAS = {
    "temperature_2m": "temp_c",
    "relative_humidity_2m": "umidade_pct",
    "precipitation": "precipitacao_mm",
    "wind_speed_10m": "vento_kmh",
    "apparent_temperature": "sensacao_c",  # NOVO
}
```

**2) Preencher valores faltantes.** A lista `_COLUNAS_INTERPOLAVEIS` diz quais
colunas têm os "buracos" preenchidos com base nos valores vizinhos. A sensação
térmica muda aos poucos, hora a hora (como a temperatura), então ela também
entra aqui:

```python
_COLUNAS_INTERPOLAVEIS = ["temperature_2m", "relative_humidity_2m", "apparent_temperature"]
```

> ❓ **Por que aqui é `"apparent_temperature"` e não `"sensacao_c"`?**
> Porque os valores faltantes são preenchidos **antes** de renomear as
> colunas (veja a ordem das etapas dentro de `clean()`). Nesse momento, a
> coluna ainda tem o nome original da API. Leia o comentário que já existe
> acima dessa lista no código: ele explica exatamente isso.

**3) Incluir a coluna no resultado final.** No fim do método `clean()`, a
lista `colunas` escolhe quais colunas saem do cleaner. Acrescente a nova:

```python
colunas = ["cidade", "datetime", "temp_c", "umidade_pct", "precipitacao_mm", "vento_kmh", "sensacao_c"]
```

**4) Atualizar os dados falsos.** No bloco `if __name__ == "__main__":`, o
dicionário `raw_mock` imita a resposta da API. Como agora a API também
devolve `apparent_temperature`, acrescente uma lista com **8 valores**
(o mesmo tamanho das outras listas). Coloque um `None` para testar o
preenchimento de faltantes:

```python
            "wind_speed_10m": [10.2, 9.8, 11.0, 9.5, 10.5, 10.0, 9.9, 500.0],
            "apparent_temperature": [24.0, 23.5, None, 23.1, 22.8, 23.6, 23.2, 23.4],  # NOVO
```

✅ Rode e confira:

```bash
python -m clima_pipeline.transform.cleaner
```

Deve aparecer uma tabela com a coluna `sensacao_c` no final, **sem** nenhum
`NaN` (o `None` que você colocou deve ter virado um número).

#### Passo B3 — Calcular a sensação térmica por dia

📄 Arquivo: [`src/clima_pipeline/transform/aggregator.py`](src/clima_pipeline/transform/aggregator.py)

**1) Criar as colunas diárias.** No método `build_daily_view`, o `.agg(...)`
cria as colunas da tabela por dia. Cada linha segue o formato
`nome_da_coluna_nova=("coluna_de_origem", "cálculo")`. Acrescente duas linhas:

```python
            .agg(
                temp_media=("temp_c", "mean"),
                temp_min=("temp_c", "min"),
                temp_max=("temp_c", "max"),
                umidade_media=("umidade_pct", "mean"),
                precipitacao_total=("precipitacao_mm", "sum"),
                vento_medio=("vento_kmh", "mean"),
                sensacao_media=("sensacao_c", "mean"),  # NOVO: média do dia
                sensacao_max=("sensacao_c", "max"),     # NOVO: maior valor do dia
            )
```

**2) Atualizar os dados falsos.** No bloco `if __name__ == "__main__":`, o
DataFrame `df_horario_mock` tem 4 linhas. Acrescente a coluna nova com **4 valores**:

```python
        "vento_kmh": [5.0, 12.0, 8.0, 15.0],
        "sensacao_c": [21.0, 28.0, 22.0, 33.0],  # NOVO
```

✅ Rode e confira:

```bash
python -m clima_pipeline.transform.aggregator
```

Devem aparecer as colunas `sensacao_media` e `sensacao_max`. Faça a conta de
cabeça para o dia 01/01: média de 21 e 28 = **24.5**; máximo = **28.0**.

#### Passo B4 — Salvar as colunas novas no banco

📄 Arquivo: [`src/clima_pipeline/load/sqlite_repository.py`](src/clima_pipeline/load/sqlite_repository.py)

Aqui são **5 mudanças**. A regra é simples: **sempre acrescente a coluna nova
no final**, tanto nas listas quanto nas tabelas.

**1) Lista de colunas da tabela por hora** (`_COLUNAS_RAW`, no topo do arquivo):

```python
_COLUNAS_RAW = ["cidade", "datetime", "temp_c", "umidade_pct", "precipitacao_mm", "vento_kmh", "sensacao_c"]
```

**2) Lista de colunas da tabela por dia** (`_COLUNAS_DIARIO`): acrescente
`"sensacao_media"` e `"sensacao_max"` no final da lista.

**3) Tabela por hora** (método `_tabela_raw`): acrescente uma coluna do tipo `Float`:

```python
            Column("vento_kmh", Float),
            Column("sensacao_c", Float),  # NOVO
        )
```

**4) Tabela por dia** (método `_tabela_diario`): acrescente, no final,
`Column("sensacao_media", Float)` e `Column("sensacao_max", Float)`.

**5) Dados falsos** (bloco `if __name__ == "__main__":`):
- em `df_raw_mock`, acrescente `"sensacao_c": [24.0, 23.5],`
- em `df_diario_mock`, acrescente `"sensacao_media": [23.8],` e `"sensacao_max": [24.0],`

✅ Rode e confira:

```bash
python -m clima_pipeline.load.sqlite_repository
```

Deve aparecer uma tabela de São Paulo com `sensacao_media` e `sensacao_max`
no final.

> ⚠️ Se aparecer o erro `table clima_raw has no column named sensacao_c`, é
> porque o arquivo `data/clima_teste.db` antigo ainda existe. Volte na seção
> [Antes de começar: faça um backup do banco](#antes-de-começar-faça-um-backup-do-banco).

#### Passo B5 — Mostrar as colunas novas na API

📄 Arquivo: [`src/clima_pipeline/api/schemas.py`](src/clima_pipeline/api/schemas.py)

A classe `ClimaDiarioOut` descreve **quais campos** a API devolve em
`/clima/diario`. Se a coluna não estiver aqui, a API não a mostra. Acrescente
os dois campos no final da classe:

```python
    ranking_temp_dia: int
    indice_conforto_c: float
    sensacao_media: float  # NOVO
    sensacao_max: float    # NOVO
```

#### Passo B6 — Mostrar no dashboard

📄 Arquivo: [`src/clima_pipeline/dashboard/app.py`](src/clima_pipeline/dashboard/app.py)

**1) Seletor do gráfico comparativo.** Procure o `st.selectbox("Variável", [...])`
e acrescente `"sensacao_media"` na lista de opções:

```python
variavel = st.selectbox(
    "Variável",
    ["temp_media", "umidade_media", "precipitacao_total", "vento_medio", "indice_conforto_c", "sensacao_media"],
    index=0,
)
```

**2) Tabela no final da página.** Procure a lista `colunas_tabela` e
acrescente `"sensacao_media"` logo depois de `"temp_max"`.

#### Passo B7 — Rodar tudo de novo

Agora que todas as etapas conhecem a coluna nova, rode o pipeline completo:

```bash
python -m clima_pipeline.pipeline
```

Depois reinicie a API e o dashboard (ou clique em "Rerun" no dashboard).

### ✅ Checklist da Funcionalidade 1

Marque cada item quando conferir. Tire um **print** de cada um para a entrega.

- [ ] O pipeline rodou para as **7 cidades** e terminou com "Pipeline concluído".
- [ ] No banco, a tabela `clima_diario` tem `sensacao_media` preenchida para Belém:
      ```bash
      sqlite3 data/clima.db "SELECT cidade, data, temp_media, sensacao_media FROM clima_diario WHERE cidade='belem' LIMIT 5;"
      ```
- [ ] Em <http://127.0.0.1:8000/docs>, o endpoint `/cidades` mostra 7 cidades.
- [ ] Em `/clima/diario`, com `cidade = PR`, aparecem os dados de Curitiba com `sensacao_media` e `sensacao_max`.
- [ ] No dashboard, Belém e Curitiba aparecem na lista de cidades.
- [ ] No dashboard, `sensacao_media` aparece no seletor do gráfico comparativo e a linha é desenhada.
- [ ] Os comandos `python -m` de `cleaner`, `aggregator` e `sqlite_repository` rodam sem erro.

---

## Funcionalidade 2 — Resumo do período

### O que é

Hoje a API devolve **uma linha por dia**. Se alguém quiser saber "qual foi o
dia mais quente de janeiro em Recife?", precisa baixar todos os dias e fazer
as contas sozinho.

Nesta funcionalidade você vai criar um endpoint novo que já devolve essas
respostas prontas, chamado **resumo**. Exemplo de chamada:

```
GET /clima/resumo?cidade=recife&inicio=2025-01-01&fim=2025-01-31
```

Exemplo de resposta:

```json
{
  "cidade": "recife",
  "inicio": "2025-01-01",
  "fim": "2025-01-31",
  "dias_analisados": 31,
  "temp_media_periodo": 27.3,
  "temp_max_absoluta": 31.2,
  "dia_mais_quente": "2025-01-17",
  "temp_min_absoluta": 23.4,
  "dia_mais_frio": "2025-01-05",
  "precipitacao_total_periodo": 182.6,
  "dias_chuvosos": 12,
  "sensacao_media_periodo": 30.2,
  "categoria_predominante": "quente"
}
```

*(os números acima são só um exemplo; os seus vão ser diferentes)*

E, no dashboard, você vai mostrar esses números em **cartões**, um grupo de
cartões para cada cidade selecionada.

### O caminho que vamos seguir

```
 Passo 1: transform/resumo.py   → função que faz as contas (arquivo NOVO)
 Passo 2: api/schemas.py        → descreve o formato da resposta
 Passo 3: api/main.py           → cria o endpoint /clima/resumo
 Passo 4: dashboard/app.py      → mostra os cartões
 Passo 5: documentação          → README e Sphinx
```

---

### Passo 1 — Criar a função que calcula o resumo

📄 Arquivo **novo**: `src/clima_pipeline/transform/resumo.py`

Crie o arquivo (botão direito na pasta `transform` → New File → `resumo.py`).

A função vai receber a **tabela por dia de uma cidade** (um DataFrame) e
devolver um **dicionário** com o resumo. Comece com esta estrutura. Algumas
chaves já estão prontas como exemplo, e as marcadas com `...` são para você completar:

```python
"""Calcula o resumo do período (estatísticas) a partir da visão diária de uma cidade."""

import datetime as dt

import pandas as pd


def calcular_resumo(df_diario: pd.DataFrame) -> dict:
    """Recebe a visão diária de UMA cidade e devolve um dicionário com o resumo do período."""
    # idxmax() devolve o NÚMERO DA LINHA (índice) onde está o maior valor.
    # Com esse número, df.loc[linha, "data"] pega a data daquela linha.
    linha_mais_quente = df_diario["temp_max"].idxmax()

    return {
        "cidade": df_diario["cidade"].iloc[0],  # iloc[0] = valor da primeira linha
        "inicio": df_diario["data"].min(),
        "fim": ...,
        "dias_analisados": len(df_diario),
        "temp_media_periodo": round(df_diario["temp_media"].mean(), 1),
        "temp_max_absoluta": ...,
        "dia_mais_quente": df_diario.loc[linha_mais_quente, "data"],
        "temp_min_absoluta": ...,
        "dia_mais_frio": ...,
        "precipitacao_total_periodo": ...,
        "dias_chuvosos": ...,
        "sensacao_media_periodo": ...,
        "categoria_predominante": ...,
    }
```

Use esta tabela para completar cada chave:

| Chave | O que significa | Como calcular (dica de pandas) |
|-------|-----------------|--------------------------------|
| `fim` | último dia do período | igual ao `inicio`, mas com `.max()` |
| `temp_max_absoluta` | a maior temperatura de todo o período | `.max()` na coluna `temp_max`, com `round(..., 1)` |
| `temp_min_absoluta` | a menor temperatura de todo o período | `.min()` na coluna `temp_min`, com `round(..., 1)` |
| `dia_mais_frio` | o dia em que aconteceu a menor temperatura | igual a `dia_mais_quente`, mas com `.idxmin()` na coluna `temp_min` |
| `precipitacao_total_periodo` | quanto choveu no período todo (em mm) | `.sum()` na coluna `precipitacao_total`, com `round(..., 1)` |
| `dias_chuvosos` | quantos dias choveu | `(df_diario["categoria_chuva"] == "chuvoso").sum()` |
| `sensacao_media_periodo` | média da sensação térmica | `.mean()` na coluna `sensacao_media`, com `round(..., 1)` |
| `categoria_predominante` | a categoria (`frio`/`ameno`/`quente`) que mais aparece | `df_diario["categoria_temp"].value_counts().idxmax()` |

> 💡 **Entendendo as duas dicas mais "estranhas":**
>
> - `(df["categoria_chuva"] == "chuvoso")` cria uma coluna de `True`/`False`
>   (um para cada dia). O `.sum()` conta os `True`, porque o Python trata
>   `True` como `1` e `False` como `0`.
> - `value_counts()` conta quantas vezes cada valor aparece, por exemplo
>   `quente: 20, ameno: 11`. O `.idxmax()` pega o nome do que apareceu mais: `"quente"`.
>
> Se tiver dúvida, teste em um notebook com um DataFrame pequeno antes!

#### Teste a sua função com dados falsos

No final do arquivo `resumo.py`, crie o bloco de teste. Aqui os dados são
pequenos para que **você consiga saber a resposta certa de cabeça**:

```python
if __name__ == "__main__":
    # Entrada mockada: 4 dias inventados de Recife, para testar calcular_resumo()
    # sem precisar da API nem do banco.
    df_mock = pd.DataFrame({
        "cidade": ["recife"] * 4,
        "data": [dt.date(2025, 1, 1), dt.date(2025, 1, 2), dt.date(2025, 1, 3), dt.date(2025, 1, 4)],
        "temp_media": [26.0, 27.0, 29.0, 28.0],
        "temp_min": [23.0, 22.5, 25.0, 24.0],
        "temp_max": [30.0, 31.0, 34.5, 32.0],
        "precipitacao_total": [0.0, 12.5, 0.0, 3.0],
        "categoria_chuva": ["seco", "chuvoso", "seco", "chuvoso"],
        "sensacao_media": [28.0, 29.5, 32.0, 30.5],
        "categoria_temp": ["quente", "quente", "quente", "quente"],
    })
    print(calcular_resumo(df_mock))
```

Rode:

```bash
python -m clima_pipeline.transform.resumo
```

✅ Confira se o resultado bate com estas respostas:

| Chave | Valor esperado | Por quê |
|-------|----------------|---------|
| `inicio` / `fim` | 2025-01-01 / 2025-01-04 | primeiro e último dia |
| `dias_analisados` | 4 | são 4 linhas |
| `temp_media_periodo` | 27.5 | (26 + 27 + 29 + 28) ÷ 4 |
| `temp_max_absoluta` / `dia_mais_quente` | 34.5 / 2025-01-03 | maior `temp_max` está no dia 3 |
| `temp_min_absoluta` / `dia_mais_frio` | 22.5 / 2025-01-02 | menor `temp_min` está no dia 2 |
| `precipitacao_total_periodo` | 15.5 | 0 + 12.5 + 0 + 3 |
| `dias_chuvosos` | 2 | dias 2 e 4 |
| `sensacao_media_periodo` | 30.0 | (28 + 29.5 + 32 + 30.5) ÷ 4 |
| `categoria_predominante` | quente | todos os dias são "quente" |

> 💡 Os números podem aparecer escritos como `np.float64(27.5)`. Isso é
> normal: é só o jeito como o pandas mostra números. O valor é 27.5.

#### Deixe a função fácil de importar

📄 Arquivo: [`src/clima_pipeline/transform/__init__.py`](src/clima_pipeline/transform/__init__.py)

Acrescente o import da função nova e o nome dela na lista `__all__`:

```python
from clima_pipeline.transform.aggregator import ClimaAggregator
from clima_pipeline.transform.cleaner import ClimaCleaner
from clima_pipeline.transform.resumo import calcular_resumo  # NOVO

__all__ = ["ClimaCleaner", "ClimaAggregator", "calcular_resumo"]
```

---

### Passo 2 — Descrever o formato da resposta

📄 Arquivo: [`src/clima_pipeline/api/schemas.py`](src/clima_pipeline/api/schemas.py)

Toda resposta da API tem uma classe que descreve os campos e seus tipos. Crie
a classe `ResumoOut` no final do arquivo, usando `ClimaDiarioOut` como modelo.
**Um campo para cada chave do dicionário do Passo 1**:

```python
class ResumoOut(BaseModel):
    """Resumo do período de uma cidade, no formato devolvido por GET /clima/resumo."""

    cidade: str
    inicio: dt.date
    fim: dt.date
    dias_analisados: int
    temp_media_periodo: float
    # ... complete com os outros campos
```

Qual tipo usar em cada campo:

| Tipo | Para quais campos |
|------|-------------------|
| `str` | textos: `cidade`, `categoria_predominante` |
| `dt.date` | datas: `inicio`, `fim`, `dia_mais_quente`, `dia_mais_frio` |
| `int` | contagens (número inteiro): `dias_analisados`, `dias_chuvosos` |
| `float` | medidas (número com vírgula): todas as temperaturas, chuva e sensação |

> ⚠️ Os nomes dos campos precisam ser **exatamente iguais** às chaves do
> dicionário do Passo 1. Um erro de digitação (ex.: `dia_mais_quente` ×
> `dia_mais_quentee`) faz a API dar erro.

---

### Passo 3 — Criar o endpoint `/clima/resumo`

📄 Arquivo: [`src/clima_pipeline/api/main.py`](src/clima_pipeline/api/main.py)

#### 3.1 — Separar o filtro de datas em uma função

O endpoint novo precisa filtrar as datas **exatamente como** o
`/clima/diario` já faz. Em vez de copiar e colar essas linhas (e ter o mesmo
código em dois lugares), vamos colocá-las em uma **função** e usá-la nos dois endpoints.

Hoje, dentro de `clima_diario`, existem estas linhas:

```python
    df["data"] = df["data"].dt.date
    if inicio:
        df = df[df["data"] >= inicio]
    if fim:
        df = df[df["data"] <= fim]
```

Crie esta função logo abaixo de `_resolver_ou_404`:

```python
def _filtrar_periodo(df: pd.DataFrame, inicio: dt.date | None, fim: dt.date | None) -> pd.DataFrame:
    """Mantém só as linhas entre `inicio` e `fim` (os dois são opcionais)."""
    df["data"] = df["data"].dt.date  # converte data+hora em só data, para comparar com inicio/fim
    if inicio:
        df = df[df["data"] >= inicio]
    if fim:
        df = df[df["data"] <= fim]
    return df
```

E, dentro de `clima_diario`, **troque** aquelas 5 linhas por uma só:

```python
    df = _filtrar_periodo(df, inicio, fim)
```

Como a função usa `pd.DataFrame`, acrescente `import pandas as pd` nos imports
do topo do arquivo.

✅ Confira em `/docs` se o `/clima/diario` continua funcionando igual a antes,
com e sem as datas.

#### 3.2 — Importar o que o endpoint novo vai usar

No topo de `main.py`, acrescente `ResumoOut` no import dos schemas e importe a função do Passo 1:

```python
from clima_pipeline.api.schemas import CidadeOut, ClimaDiarioOut, HealthOut, ResumoOut
from clima_pipeline.transform import calcular_resumo
```

#### 3.3 — Criar o endpoint

No final do arquivo, crie o endpoint. Ele é muito parecido com o
`clima_diario`, então compare os dois lado a lado:

```python
@app.get("/clima/resumo", response_model=ResumoOut)
def clima_resumo(
    cidade: str = Query(..., description="Slug, nome de exibição ou UF da cidade"),
    inicio: dt.date | None = Query(None, description="Data inicial (YYYY-MM-DD)"),
    fim: dt.date | None = Query(None, description="Data final (YYYY-MM-DD)"),
) -> ResumoOut:
    """Devolve o resumo do período (dia mais quente, total de chuva, etc.) de uma cidade."""
    # 1) transforma o texto recebido (ex.: "SP") no slug (ex.: "sao_paulo"),
    #    ou devolve erro 404 se a cidade não existir
    slug = _resolver_ou_404(cidade)

    # 2) busca no banco a visão diária dessa cidade
    df = get_repository().get_daily(city=slug)

    # 3) se o banco não tem nada dessa cidade, devolve erro 404
    if df.empty:
        raise HTTPException(status_code=404, detail="Sem dados para o período informado.")

    # 4) filtra pelo período pedido
    df = ...  # use a função _filtrar_periodo

    # 5) se depois do filtro não sobrou nenhum dia, também devolve 404
    #    (complete: é igual ao passo 3)

    # 6) calcula o resumo e devolve no formato de ResumoOut
    resumo = calcular_resumo(df)
    return ResumoOut(**resumo)
```

> ❓ **Por que devolver erro 404 quando não há dados?**
> O `/clima/diario` pode devolver uma lista vazia (`[]`), mas o resumo não
> tem como calcular "o dia mais quente" de zero dias: o `idxmax()` daria
> erro. O código 404 significa "não encontrado", e é a forma certa de a API
> dizer "não tenho dados para isso".

> ❓ **O que é `ResumoOut(**resumo)`?**
> Os `**` "abrem" o dicionário e passam cada chave como um parâmetro. É o
> mesmo que escrever `ResumoOut(cidade=resumo["cidade"], inicio=resumo["inicio"], ...)`,
> só que bem mais curto. O `/clima/diario` já usa esse truque.

#### 3.4 — Atualizar o comentário do topo

A docstring no começo de `main.py` diz que *"a API só tem 2 endpoints de dado"*.
Atualize esse texto para mencionar o endpoint novo `/clima/resumo`.

✅ Teste em <http://127.0.0.1:8000/docs>: clique em `/clima/resumo` →
**Try it out** → preencha → **Execute**. Teste estes 4 casos:

| Teste | O que preencher | Resultado esperado |
|-------|-----------------|--------------------|
| Caso normal | `cidade = SP` | código **200** e o resumo de São Paulo |
| Com período | `cidade = recife`, `inicio = 2025-01-10`, `fim = 2025-01-15` | código **200** com `dias_analisados = 6` |
| Cidade que não existe | `cidade = cidade_inexistente` | código **404** |
| Período sem dados | `cidade = recife`, `inicio = 2030-01-01` | código **404** com a mensagem "Sem dados para o período informado." |

---

### Passo 4 — Mostrar o resumo no dashboard

📄 Arquivo: [`src/clima_pipeline/dashboard/app.py`](src/clima_pipeline/dashboard/app.py)

#### 4.1 — Função que busca o resumo na API

Logo abaixo da função `carregar_diario`, crie uma função parecida para o resumo:

```python
@st.cache_data(ttl=60)
def carregar_resumo(base_url: str, slug: str, inicio: dt.date, fim: dt.date) -> dict:
    """Busca o resumo do período de UMA cidade na API. Cacheada por 1 min."""
    params = {"cidade": slug, "inicio": str(inicio), "fim": str(fim)}
    resposta = requests.get(f"{base_url}/clima/resumo", params=params, timeout=10)
    resposta.raise_for_status()  # se a API devolver erro (ex.: 404), lança uma exceção
    return resposta.json()       # o JSON da resposta vira um dicionário Python
```

> 💡 O `@st.cache_data(ttl=60)` guarda o resultado por 60 segundos. Se você
> mudar algo na API e o dashboard continuar mostrando o valor antigo, aperte
> a tecla **C** na página do dashboard para limpar o cache.

#### 4.2 — A seção de cartões

Procure a linha `diario["nome_exibicao"] = diario["cidade"].map(nome_por_slug)`.
Logo **depois** dela, e **antes** do comentário `# --- Gráfico 1`, acrescente a
seção de resumo:

```python
# --- Resumo do período: um grupo de cartões (st.metric) para cada cidade ---
st.subheader("Resumo do período")

# st.columns(n) divide a tela em n colunas lado a lado, uma para cada cidade
colunas_tela = st.columns(len(slugs_selecionados))

# zip() percorre as duas listas juntas: a 1ª coluna com a 1ª cidade, a 2ª com a 2ª...
for coluna, slug in zip(colunas_tela, slugs_selecionados):
    with coluna:  # tudo dentro deste "with" aparece nesta coluna da tela
        st.markdown(f"**{nome_por_slug[slug]}**")
        try:
            resumo = carregar_resumo(api_base_url, slug, inicio, fim)
        except requests.RequestException as erro:
            st.warning(f"Sem resumo: {erro}")
            continue  # pula para a próxima cidade

        st.metric("Temperatura média", f"{resumo['temp_media_periodo']:.1f} °C")
        st.metric(
            "Máxima do período",
            f"{resumo['temp_max_absoluta']:.1f} °C",
            help=f"Registrada em {resumo['dia_mais_quente']}",
        )
        # complete com pelo menos mais 2 cartões:
        # - "Chuva total", usando resumo['precipitacao_total_periodo'] e a unidade "mm"
        # - "Dias chuvosos", usando resumo['dias_chuvosos']
```

> 💡 **Entendendo o `f"{valor:.1f} °C"`:** o `:.1f` mostra o número com
> **1 casa decimal** (27.3456 vira `27.3`).

> 💡 **Por que o `try/except`?** Se a API falhar para uma cidade (por
> exemplo, sem dados no período), mostramos um aviso só naquela coluna e as
> outras cidades continuam aparecendo. O próprio `app.py` já faz isso ao
> carregar o diário: dê uma olhada lá.

✅ Abra o dashboard e confira:
- aparecem os cartões de resumo, uma coluna para cada cidade selecionada;
- ao passar o mouse no ícone **?** do cartão "Máxima do período", aparece a data;
- ao mudar as datas na barra lateral, os números mudam.

---

### Passo 5 — Documentação

**1) Sphinx.** Abra [`docs/api/transform.rst`](docs/api/transform.rst) e
acrescente no final (igual aos blocos que já existem):

```rst
``resumo``
----------

.. automodule:: clima_pipeline.transform.resumo
```

**2) README.** No [`README.md`](README.md), na seção "Rodando a API", a linha
`Endpoints:` lista os endpoints existentes. Acrescente o `/clima/resumo`. Na
seção "Sobre o projeto", atualize o texto que fala das "5 cidades" para as 7.

### ✅ Checklist da Funcionalidade 2

Marque cada item quando conferir. Tire um **print** de cada um para a entrega.

- [ ] `python -m clima_pipeline.transform.resumo` mostra os valores esperados da tabela do Passo 1.
- [ ] Em `/docs`, os 4 testes do Passo 3 dão os resultados esperados (200, 200, 404, 404).
- [ ] O `/clima/diario` continua funcionando (agora usando `_filtrar_periodo`).
- [ ] As linhas que filtram por data aparecem **uma vez só** no código, dentro de `_filtrar_periodo`.
- [ ] O dashboard mostra os cartões de resumo de cada cidade selecionada.
- [ ] Os cartões mudam quando as datas mudam na barra lateral.
- [ ] `docs/api/transform.rst` e `README.md` foram atualizados.

---

## Problemas comuns e como resolver

| Mensagem de erro (ou sintoma) | O que provavelmente aconteceu | Como resolver |
|-------------------------------|-------------------------------|---------------|
| `ModuleNotFoundError: No module named 'clima_pipeline'` | O ambiente virtual não está ativado, ou o projeto não foi instalado | Ative o `.venv` e rode `pip install -e .` (veja a [Parte 0](#parte-0--preparando-o-ambiente)) |
| `SyntaxError` apontando para `config.py` | Faltou uma vírgula ou uma chave `}` no dicionário `CIDADES` | Compare a sua cidade nova com uma das cidades antigas, linha por linha |
| `table clima_raw has no column named sensacao_c` (ou `clima_diario ... sensacao_media`) | O banco antigo ainda existe e não tem as colunas novas | Renomeie `data/clima.db` e `data/clima_teste.db` e rode de novo |
| `KeyError: 'sensacao_c'` ou `"['sensacao_c'] not in index"` | A coluna não chegou até aquela etapa: faltou algum passo antes | Refaça o checklist dos Passos B1 a B3. Verifique também se colocou a coluna nos **dados falsos** do `__main__` |
| `KeyError: "['sensacao_media'] not in index"` ao salvar | O `aggregator.py` não está criando a coluna | Confira o Passo B3 (as duas linhas novas no `.agg`) |
| `ValueError: All arrays must be of the same length` no `cleaner` | A lista `apparent_temperature` do `raw_mock` não tem 8 valores | Conte os valores: precisam ser 8, como nas outras listas |
| Erro **500** na API com `Field required` | O schema pede um campo que não veio do banco ou do resumo | Confira se os nomes em `schemas.py` estão **iguais** aos das colunas/chaves e se você rodou o pipeline com o banco novo |
| `NameError: name 'pd' is not defined` em `main.py` | Faltou importar o pandas | Acrescente `import pandas as pd` no topo |
| `Can only use .dt accessor with datetimelike values` | `_filtrar_periodo` foi chamada duas vezes no mesmo DataFrame | Chame a função **uma vez só** em cada endpoint |
| Dashboard mostra "Não foi possível falar com a API" | A API não está rodando | Suba a API em outro terminal (`uvicorn ...`) |
| Dashboard não mostra a mudança que você fez | O cache do Streamlit ainda guarda o valor antigo | Aperte **C** na página para limpar o cache e depois **R** para recarregar |
| A API não mostra a mudança que você fez | A API foi iniciada sem `--reload` | Pare a API (`Ctrl + C`) e suba de novo |

> 💡 **Dica para ler erros:** a mensagem mais importante fica quase sempre na
> **última linha** do erro. Logo acima dela aparece o arquivo e o número da
> linha onde o problema aconteceu.

---

## O que entregar

1. **O código** com as duas funcionalidades funcionando.
2. **Um arquivo `ENTREGA.md`** na raiz do projeto, contendo:
   - os dois checklists (Funcionalidade 1 e 2) com os itens marcados (`- [x]`);
   - um **print** para cada item do checklist (terminal, página `/docs` e dashboard);
   - um parágrafo curto contando: qual foi a parte mais difícil e como você resolveu.

   Para colocar um print no `.md`, salve a imagem em uma pasta `prints/` e escreva:
   ```markdown
   ![Pipeline rodando para 7 cidades](prints/pipeline_7_cidades.png)
   ```
3. **Se estiver usando git:** pelo menos um commit por funcionalidade, com uma
   mensagem que diga o que foi feito (ex.: `adiciona sensação térmica ao pipeline`).

---

## Como o trabalho será avaliado

| O que será avaliado | Peso | O que esperamos |
|---------------------|------|-----------------|
| Funciona | 50% | Todos os itens dos dois checklists funcionando, comprovados com prints no `ENTREGA.md` |
| Testes com dados falsos | 15% | Os blocos `if __name__ == "__main__":` atualizados (e o novo, em `resumo.py`) rodando sem erro |
| Organização do código | 20% | Cada coisa no arquivo certo (contas em `transform/`, endpoint em `api/`, tela em `dashboard/`); sem código copiado e colado; nomes em português, como no resto do projeto |
| Documentação | 15% | Docstring (a frase entre `"""` logo abaixo do `def`) em toda função nova; `README.md` e `docs/api/transform.rst` atualizados |

Bom trabalho! 🚀
