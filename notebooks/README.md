# Notebooks

Sequência de notebooks introdutórios do projeto, cada um partindo do resultado do
anterior. Recomenda-se segui-los em ordem:

| Notebook | Conteúdo |
|---|---|
| [01_extracao_open_meteo.ipynb](01_extracao_open_meteo.ipynb) | Parte 1 — extração via `requests`, consumo da Historical Weather API (Open-Meteo) e persistência do JSON bruto em `data/raw/` |
| [02_tratamento_pandas.ipynb](02_tratamento_pandas.ipynb) | Parte 2 — tratamento com `pandas`: tipos, timezone, duplicidade, valores faltantes, outliers e otimização de memória (`category`, downcast de `float`) |
| [03_nova_visao_agregacoes.ipynb](03_nova_visao_agregacoes.ipynb) | Parte 3 — agregações e features derivadas: `groupby`, `resample`, `rolling`, `pivot_table`, `merge`, `apply`/`lambda` vs. versão vetorizada com `np.where`/`np.select` |
| [04_exploracao_visual.ipynb](04_exploracao_visual.ipynb) | Parte 3.2 — exploração visual com `matplotlib`/`seaborn`, interpretação de gráficos |
| [05_sqlite_persistencia.ipynb](05_sqlite_persistencia.ipynb) | Parte 4 — persistência com `sqlite3` puro e depois com `SQLAlchemy` |
| [06_boas_praticas_python.ipynb](06_boas_praticas_python.ipynb) | Parte 5 — boas práticas de Python: type hints (`\| None`, `@dataclass`), `try`/`except` específico e `logging` com níveis, aplicados à função de extração da Parte 1 |

O restante deste documento é a referência teórica de SQLite e SQLAlchemy usada na
Parte 4 e reaproveitada em produção por [`src/clima_pipeline/load/sqlite_repository.py`](../src/clima_pipeline/load/sqlite_repository.py).

## Sumário

- [SQLite](#sqlite)
  - [O que é e quando usar](#o-que-é-e-quando-usar)
  - [Tipagem dinâmica (type affinity)](#tipagem-dinâmica-type-affinity)
  - [Conectando com `sqlite3` (biblioteca padrão)](#conectando-com-sqlite3-biblioteca-padrão)
  - [Criando tabelas e chaves primárias](#criando-tabelas-e-chaves-primárias)
  - [CRUD manual com `sqlite3`](#crud-manual-com-sqlite3)
  - [Transações e `commit`](#transações-e-commit)
  - [`UPSERT` (`INSERT ... ON CONFLICT`)](#upsert-insert--on-conflict)
  - [Integração com pandas: `to_sql` e `read_sql`](#integração-com-pandas-to_sql-e-read_sql)
  - [Concorrência e limitações do SQLite](#concorrência-e-limitações-do-sqlite)
- [SQLAlchemy](#sqlalchemy)
  - [Por que uma camada acima do `sqlite3`](#por-que-uma-camada-acima-do-sqlite3)
  - [Core vs. ORM](#core-vs-orm)
  - [`Engine`: a porta de entrada para o banco](#engine-a-porta-de-entrada-para-o-banco)
  - [`MetaData`, `Table` e `Column` (Core)](#metadata-table-e-column-core)
  - [Construindo queries com a linguagem de expressão](#construindo-queries-com-a-linguagem-de-expressão)
  - [Transações com `engine.begin()` / `engine.connect()`](#transações-com-enginebegin--engineconnect)
  - [`UPSERT` idiomático (`sqlite.insert().on_conflict_do_update`)](#upsert-idiomático-sqliteinserton_conflict_do_update)
  - [ORM: um vislumbre](#orm-um-vislumbre)
  - [Quando escolher `sqlite3` puro, Core ou ORM](#quando-escolher-sqlite3-puro-core-ou-orm)
- [Referências](#referências)

## SQLite

### O que é e quando usar

[SQLite](https://www.sqlite.org/index.html) é um banco de dados relacional
**embarcado**: não roda como um processo servidor separado (diferente de
PostgreSQL ou MySQL) — a biblioteca lê e escreve diretamente em **um único
arquivo** no disco (ex.: `data/clima.db`). Isso o torna ideal para:

- Projetos pequenos/médios, protótipos e pipelines de dados locais.
- Aplicações desktop/mobile (é o banco embutido do Android e do iOS).
- Armazenar o resultado de um pipeline ETL que roda em uma única máquina, como
  neste projeto.

Não é a escolha ideal quando há **muitas escritas concorrentes** vindas de
processos diferentes (ver [Concorrência](#concorrência-e-limitações-do-sqlite))
ou quando o dado precisa ser acessado por múltiplos servidores ao mesmo tempo —
nesses casos, um banco cliente-servidor (PostgreSQL, MySQL) é mais adequado.

### Tipagem dinâmica (type affinity)

Diferente da maioria dos bancos relacionais, o SQLite usa **tipagem dinâmica
por afinidade**: uma coluna declarada como `INTEGER` aceita guardar um texto,
por exemplo — o tipo declarado é uma *sugestão* de conversão, não uma restrição
rígida. As afinidades são: `TEXT`, `NUMERIC`, `INTEGER`, `REAL`, `BLOB`. Na
prática, para os tipos usuais (`str`, `int`, `float`, `datetime` como texto
ISO), isso é transparente — mas vale saber que o SQLite é mais permissivo que
um PostgreSQL, por exemplo, que rejeitaria a inserção de um texto numa coluna
`INTEGER`.

### Conectando com `sqlite3` (biblioteca padrão)

O módulo [`sqlite3`](https://docs.python.org/3/library/sqlite3.html) já vem
com o Python — não precisa instalar nada:

```python
import sqlite3

conexao = sqlite3.connect("data/clima.db")  # cria o arquivo se não existir
cursor = conexao.cursor()
```

`conexao` representa a conexão com o arquivo; `cursor` é o objeto usado para
executar comandos SQL e iterar sobre resultados.

### Criando tabelas e chaves primárias

```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS clima_raw (
        cidade   TEXT,
        datetime TEXT,
        temp_c   REAL,
        PRIMARY KEY (cidade, datetime)
    )
""")
conexao.commit()
```

- `IF NOT EXISTS` evita erro se a tabela já existir (idempotente — pode rodar o
  script várias vezes sem quebrar).
- `PRIMARY KEY (cidade, datetime)` aqui é uma **chave composta**: a combinação
  das duas colunas é única, permitindo `UPSERT` por (cidade, timestamp) — é
  exatamente o padrão usado em `clima_raw` e `clima_diario` neste projeto.

### CRUD manual com `sqlite3`

```python
# INSERT — sempre com placeholders (?), nunca f-string/concatenação (SQL injection)
cursor.execute(
    "INSERT INTO clima_raw (cidade, datetime, temp_c) VALUES (?, ?, ?)",
    ("sao_paulo", "2025-01-01T00:00", 24.3),
)

# INSERT em lote
cursor.executemany(
    "INSERT INTO clima_raw (cidade, datetime, temp_c) VALUES (?, ?, ?)",
    [("recife", "2025-01-01T00:00", 27.1), ("recife", "2025-01-01T01:00", 26.8)],
)

# SELECT
cursor.execute("SELECT * FROM clima_raw WHERE cidade = ?", ("sao_paulo",))
linhas = cursor.fetchall()  # lista de tuplas

# UPDATE
cursor.execute(
    "UPDATE clima_raw SET temp_c = ? WHERE cidade = ? AND datetime = ?",
    (24.5, "sao_paulo", "2025-01-01T00:00"),
)

# DELETE
cursor.execute("DELETE FROM clima_raw WHERE cidade = ?", ("sao_paulo",))
```

**Sempre** use `?` como placeholder para valores vindos de variáveis — nunca
monte a string SQL com f-string/`.format()`/concatenação, isso abre brecha para
**SQL injection**.

### Transações e `commit`

O `sqlite3` abre uma transação implícita a cada `INSERT`/`UPDATE`/`DELETE` — as
mudanças só ficam permanentes no arquivo após `conexao.commit()`. Se algo der
errado antes do commit, `conexao.rollback()` desfaz tudo o que foi feito desde
o último commit. Isso garante atomicidade: ou o lote inteiro de mudanças é
gravado, ou nenhuma é.

```python
try:
    cursor.execute("INSERT INTO clima_raw VALUES (...)")
    cursor.execute("INSERT INTO clima_diario VALUES (...)")
    conexao.commit()
except Exception:
    conexao.rollback()
    raise
```

### `UPSERT` (`INSERT ... ON CONFLICT`)

Quando o pipeline roda de novo para o mesmo período, não queremos duplicar
linhas nem falhar por violar a chave primária — queremos **inserir se não
existe, atualizar se já existe**. O SQLite suporta isso nativamente desde a
versão 3.24 com a cláusula `ON CONFLICT`:

```sql
INSERT INTO clima_raw (cidade, datetime, temp_c)
VALUES (?, ?, ?)
ON CONFLICT (cidade, datetime) DO UPDATE SET temp_c = excluded.temp_c;
```

`excluded` é uma tabela virtual que representa a linha que *tentou* ser
inserida e colidiu — é assim que se referencia "o valor novo" na cláusula de
update.

### Integração com pandas: `to_sql` e `read_sql`

O pandas fala com qualquer banco suportado pelo SQLAlchemy (inclusive SQLite)
através de duas funções:

```python
import pandas as pd

df.to_sql("clima_raw", conexao, if_exists="append", index=False)

df_lido = pd.read_sql("SELECT * FROM clima_raw", conexao, parse_dates=["datetime"])
```

- `if_exists`: `"fail"` (padrão, erro se a tabela existe), `"replace"` (dropa e
  recria) ou `"append"` (adiciona linhas — **não faz upsert**, duplica se
  rodado duas vezes com os mesmos dados).
- `to_sql` é conveniente para prototipagem, mas não substitui um `UPSERT`
  manual quando idempotência importa — por isso o pipeline de produção
  (`SQLiteRepository`) usa `INSERT ... ON CONFLICT` via SQLAlchemy em vez de
  `to_sql`.

### Concorrência e limitações do SQLite

- **Um escritor por vez**: o SQLite trava o arquivo inteiro (ou, no modo
  [WAL](https://www.sqlite.org/wal.html), a escrita é mais concorrente com
  leituras) durante uma escrita — múltiplos processos escrevendo ao mesmo
  tempo podem receber `database is locked`.
  - No modo WAL, escritores continuam bloqueando-se entre si, mas leitores não
    bloqueiam escritores nem vice-versa — na prática, é a configuração
    recomendada para qualquer uso além do trivial: `PRAGMA journal_mode=WAL;`.
- **Sem controle de acesso**: qualquer processo com acesso ao arquivo tem
  acesso total ao banco (não há usuários/permissões como em PostgreSQL).
- **Tamanho**: funciona bem até dezenas de GB, mas não foi desenhado para os
  volumes e cargas de um banco cliente-servidor dedicado.

## SQLAlchemy

### Por que uma camada acima do `sqlite3`

Escrever SQL cru funciona, mas tem custos: strings SQL espalhadas pelo código,
sem checagem em tempo de "compilação", trocar de banco (SQLite → PostgreSQL)
exige reescrever queries, e é fácil escorregar em SQL injection ao concatenar
strings. O [SQLAlchemy](https://docs.sqlalchemy.org/) resolve isso oferecendo:

- Uma API Python para descrever schema e queries (a *linguagem de expressão*),
  que gera SQL correto para o dialeto do banco em uso.
- Um `Engine` com **connection pooling** já embutido.
- Um ORM opcional para mapear tabelas a classes Python.

### Core vs. ORM

SQLAlchemy tem duas camadas:

- **Core** — descreve tabelas (`Table`, `Column`) e queries (`select`,
  `insert`, `update`...) como objetos Python, mas o resultado de uma query
  ainda é linhas "cruas" (tuplas/mappings), não objetos de domínio. É a camada
  usada neste projeto (`SQLiteRepository`), por ser mais direta para um
  pipeline de dados que já trabalha com `pandas.DataFrame`.
- **ORM** (Object-Relational Mapper) — camada acima do Core que mapeia cada
  tabela a uma classe Python e cada linha a uma instância dessa classe,
  gerenciando identidade, relacionamentos (`relationship()`) e um "unit of
  work" (`Session`). Mais poderoso para modelar domínios ricos com muitas
  relações entre entidades; overhead desnecessário quando o objetivo é
  ler/escrever `DataFrame`s inteiros, como aqui.

### `Engine`: a porta de entrada para o banco

```python
from sqlalchemy import create_engine

engine = create_engine("sqlite:///data/clima.db")
```

A *connection string* segue o formato `dialeto+driver://usuario:senha@host/banco`;
para SQLite, como não há servidor, é só `sqlite:///caminho/do/arquivo.db`
(três barras = caminho relativo; `sqlite:////caminho/absoluto.db` com quatro
barras = caminho absoluto no Linux/macOS). O `Engine` gerencia um **pool de
conexões** internamente — normalmente se cria **um único `Engine` por
processo** (não um por request/operação), e é isso que `SQLiteRepository.__init__`
faz.

### `MetaData`, `Table` e `Column` (Core)

`MetaData` é um catálogo que agrupa as definições de tabelas; `Table` descreve
uma tabela e suas `Column`s:

```python
from sqlalchemy import MetaData, Table, Column, String, Float, create_engine

metadata = MetaData()

clima_raw = Table(
    "clima_raw",
    metadata,
    Column("cidade", String, primary_key=True),
    Column("datetime", String, primary_key=True),
    Column("temp_c", Float),
)

engine = create_engine("sqlite:///data/clima.db")
metadata.create_all(engine, checkfirst=True)  # equivalente ao CREATE TABLE IF NOT EXISTS
```

Isso é exatamente o padrão em
[`SQLiteRepository._tabela_raw`](../src/clima_pipeline/load/sqlite_repository.py) —
o schema vira código Python versionável, em vez de um script `.sql` solto.

### Construindo queries com a linguagem de expressão

```python
from sqlalchemy import select

query = select(clima_raw).where(clima_raw.c.cidade == "sao_paulo")
```

`clima_raw.c.cidade` acessa a coluna `cidade` da tabela (o `.c` é a coleção de
colunas). O objeto `query` não executa nada sozinho — ele é compilado para SQL
apenas quando executado:

```python
with engine.connect() as conexao:
    resultado = conexao.execute(query)
    for linha in resultado:
        print(linha)

# ou, direto para um DataFrame:
import pandas as pd
df = pd.read_sql(query, engine, parse_dates=["datetime"])
```

pandas aceita tanto uma string SQL quanto um objeto de query do SQLAlchemy em
`read_sql`/`to_sql` — por isso o projeto passa a `Table`/`select()` diretamente
em vez de escrever a query como string.

### Transações com `engine.begin()` / `engine.connect()`

- `engine.connect()` abre uma conexão "crua" — quem chama precisa gerenciar
  commit/rollback manualmente.
- `engine.begin()` abre uma conexão **dentro de uma transação**: se o bloco
  `with` terminar sem exceção, faz commit automaticamente; se lançar exceção,
  faz rollback. É o padrão recomendado para qualquer escrita:

```python
with engine.begin() as conexao:
    conexao.execute(stmt)
# commit automático ao sair do bloco sem erro
```

### `UPSERT` idiomático (`sqlite.insert().on_conflict_do_update`)

O dialeto SQLite do SQLAlchemy expõe uma variante de `insert()` com suporte a
`ON CONFLICT`:

```python
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

stmt = sqlite_upsert(clima_raw).values(registros)  # registros: list[dict]
stmt = stmt.on_conflict_do_update(
    index_elements=["cidade", "datetime"],       # colunas da chave/constraint em conflito
    set_={"temp_c": stmt.excluded.temp_c},        # "temp_c" = valor que tentou ser inserido
)

with engine.begin() as conexao:
    conexao.execute(stmt)
```

`stmt.excluded` é o equivalente Python da tabela virtual `excluded` do SQL cru
— referencia os valores que colidiram com uma linha existente. Esse é
literalmente o mecanismo usado em `SQLiteRepository._upsert` para tornar
`save_raw`/`save_daily` idempotentes (rodar o pipeline de novo atualiza em vez
de duplicar).

### ORM: um vislumbre

Para contraste, a mesma tabela via ORM (não usado neste projeto, mas útil
para saber quando migrar):

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float

class Base(DeclarativeBase):
    pass

class ClimaRaw(Base):
    __tablename__ = "clima_raw"
    cidade: Mapped[str] = mapped_column(String, primary_key=True)
    datetime: Mapped[str] = mapped_column(String, primary_key=True)
    temp_c: Mapped[float] = mapped_column(Float)

# uso, com Session:
from sqlalchemy.orm import Session
with Session(engine) as sessao:
    sessao.add(ClimaRaw(cidade="sao_paulo", datetime="2025-01-01T00:00", temp_c=24.3))
    sessao.commit()
```

O ganho do ORM aparece quando há **relacionamentos entre tabelas**
(`relationship()`, joins automáticos por navegação de atributo,
carregamento preguiçoso/antecipado) — não é o caso de `clima_raw`/`clima_diario`,
que são duas tabelas independentes.

### Quando escolher `sqlite3` puro, Core ou ORM

| Cenário | Escolha |
|---|---|
| Script pequeno, sem necessidade de portar para outro banco | `sqlite3` puro |
| Pipeline de dados que já trabalha com `DataFrame`s, upsert idempotente, possível troca de banco no futuro | SQLAlchemy **Core** (usado neste projeto) |
| Domínio rico com muitas entidades relacionadas, regras de negócio orientadas a objeto | SQLAlchemy **ORM** |

## Referências

- [Documentação oficial do SQLite](https://www.sqlite.org/docs.html)
- [`sqlite3` — Python standard library](https://docs.python.org/3/library/sqlite3.html)
- [SQLite `UPSERT`](https://www.sqlite.org/lang_upsert.html)
- [SQLite WAL mode](https://www.sqlite.org/wal.html)
- [SQLAlchemy — documentação oficial](https://docs.sqlalchemy.org/)
- [SQLAlchemy Unified Tutorial (Core + ORM)](https://docs.sqlalchemy.org/en/20/tutorial/index.html)
- [SQLAlchemy Core: Working with Data](https://docs.sqlalchemy.org/en/20/core/dml.html)
- [pandas: `read_sql` / `to_sql`](https://pandas.pydata.org/docs/reference/api/pandas.read_sql.html)
