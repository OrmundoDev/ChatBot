# 7. Embeddings

## 7.1 O que é um vetor, antes de tudo

Um **vetor**, neste contexto, é simplesmente uma lista ordenada de números
(ex: `[0.021, -0.384, 0.117, ...]`). O que torna isso útil para IA é que
existe uma forma matemática de medir a "distância" ou "similaridade" entre
dois vetores — dois vetores parecidos (matematicamente próximos) representam
conceitos parecidos, mesmo que o texto original use palavras completamente
diferentes.

## 7.2 O que é um embedding

Um **embedding** é o processo (e o resultado) de transformar um texto
qualquer nesse vetor de números, de um jeito que preserva o *significado* do
texto — não é uma codificação letra-por-letra, é gerado por um modelo de IA
treinado especificamente para isso. Dois textos com significados parecidos
("qual o preço do plano?" e "quanto custa o plano?") geram vetores
matematicamente próximos, mesmo usando palavras diferentes. É essa
propriedade que permite **busca semântica**: buscar por significado, não por
coincidência exata de palavras (diferente de um `LIKE '%preço%'` no SQL, que
só acharia a segunda pergunta se a palavra "preço" aparecesse literalmente).

## 7.3 Implementação real (`embedding_service.py`)

```python
from openai import AsyncOpenAI
from app.core.config import settings

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def gerar_embedding(texto: str) -> list[float]:
    resposta = await _client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texto,
    )
    return resposta.data[0].embedding
```

O modelo usado é `text-embedding-3-small` (definido em `EMBEDDING_MODEL`,
`app/core/config.py`), que gera vetores de **1536 posições** (1536 números
por texto, sempre — não importa se o texto de entrada tem 5 ou 500
caracteres).

## 7.4 Quando embeddings são gerados

Em dois momentos, sempre:

1. **Na ingestão** (`scripts/ingest_documents.py`): um embedding é gerado
   para **cada chunk** de cada documento, e salvo permanentemente na coluna
   `chunks.embedding`.
2. **Na busca (a cada pergunta recebida)** (`KnowledgeService.search`): a
   pergunta do usuário também vira um embedding, na hora, para poder ser
   comparada matematicamente com os embeddings já salvos.

## 7.5 Onde são armazenados

Na tabela `chunks`, coluna `embedding`, tipo `vector(1536)` — um tipo de
dado especial fornecido pela extensão **pgvector** do PostgreSQL (ver
`CREATE EXTENSION IF NOT EXISTS vector` na migration, capítulo 4). Sem essa
extensão, o Postgres não saberia como guardar nem comparar vetores
matematicamente.

## 7.6 Como a busca funciona de fato (`KnowledgeService.search`)

```python
query = (
    select(Chunk)
    .order_by(Chunk.embedding.cosine_distance(embedding_pergunta))
    .limit(limit)
)
if company_id:
    query = query.where(Chunk.company_id == cid)
```

`cosine_distance` é a operação que o `pgvector` disponibiliza para medir
"distância angular" entre dois vetores — quanto menor a distância, mais
parecido o significado. A query pede: "dentre os chunks desta empresa,
ordene do mais parecido com a pergunta para o menos parecido, e me dê os 3
primeiros" (`limit=3`, valor padrão). Esses 3 chunks viram o "contexto" que
é injetado no prompt enviado à IA (ver `PromptBuilder`,
[capítulo 17](./17-fluxo-completo-mensagem.md)).

## 7.7 Quando embeddings precisam ser recriados

Sempre que o **modelo de embedding muda** (ex: trocar
`text-embedding-3-small` por outro modelo, ou trocar de provedor — OpenAI
para outro). Isso acontece porque vetores gerados por modelos diferentes não
são comparáveis entre si matematicamente — mesmo que tenham o mesmo número
de posições, os "eixos" do espaço vetorial são diferentes. Isso já aconteceu
uma vez neste projeto: a migração de Ollama (`bge-m3`, 1024 dimensões) para
OpenAI (`text-embedding-3-small`, 1536 dimensões) exigiu apagar/recriar
tanto a definição da coluna (`vector(1024)` → `vector(1536)`, em dois
lugares: a migration e o model `chunk.py` — ver
[capítulo 18, Troubleshooting](./18-troubleshooting.md)) quanto todos os
embeddings já salvos, já que os antigos simplesmente não tinham mais
compatibilidade dimensional com os novos.

**Regra prática:** se você mudar `EMBEDDING_MODEL` em `config.py`, todos os
chunks existentes precisam ser reprocessados (apagar e reingerir, ver
[capítulo 5.6](./05-base-de-conhecimento.md)) — não existe conversão
automática entre modelos de embedding diferentes.

## 7.8 Custo computacional

Cada chamada de embedding é uma requisição HTTP à API da OpenAI, cobrada por
quantidade de texto (tokens) processado. O custo por chunk é pequeno
individualmente, mas cresce com o volume de documentos ingeridos — vale
ingerir só o que realmente será consultado, evitando duplicar conteúdo
desnecessariamente entre documentos.
