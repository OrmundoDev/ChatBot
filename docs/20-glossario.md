# 20. Glossário

**API** — Application Programming Interface. Um conjunto de regras que
permite que dois sistemas diferentes troquem informação entre si.

**BSP (Business Solution Provider)** — empresa homologada pela Meta que atua
como intermediária da WhatsApp Cloud API, oferecendo sua própria URL e
token, geralmente simplificando o processo de verificação. Exemplo neste
projeto: Datafy.

**Chunk** — um pedaço menor de um texto maior, gerado ao dividir um
documento para processamento (ver [capítulo 6](./06-chunking.md)).

**Container** — um processo isolado, com suas próprias dependências,
rodando sobre o Docker, sem precisar emular um sistema operacional inteiro
(diferente de uma máquina virtual).

**Docker** — ferramenta de empacotamento e isolamento de aplicações em
containers.

**Docker Compose** — ferramenta que orquestra múltiplos containers
descritos num único arquivo (`docker-compose.yml`).

**Embedding** — a representação numérica (vetor) de um texto, gerada por um
modelo de IA, que preserva o significado semântico do texto original (ver
[capítulo 7](./07-embeddings.md)).

**FastAPI** — framework web em Python usado para construir a API deste
projeto.

**FK (Foreign Key / Chave Estrangeira)** — uma coluna que referencia o `id`
de outra tabela, garantindo integridade relacional (ex: `agents.company_id`
sempre aponta para um `companies.id` existente).

**Índice (banco de dados)** — uma estrutura auxiliar que acelera buscas em
colunas específicas, às custas de um pequeno custo extra em cada escrita.

**LLM (Large Language Model)** — modelo de linguagem de grande porte,
capaz de gerar texto (ex: os modelos da OpenAI usados neste projeto).

**Migration** — um arquivo versionado que descreve uma mudança no schema do
banco de dados (ver [capítulo 4.1](./04-banco-de-dados.md)).

**Multi-tenant** — arquitetura em que um único sistema atende múltiplos
clientes (tenants) de forma isolada entre si, sem instalações separadas por
cliente.

**n8n** — ferramenta de automação visual, usada de forma legada neste
projeto (ver [capítulo 15](./15-n8n.md)).

**ORM (Object-Relational Mapping)** — técnica que representa tabelas do
banco como classes de código (neste projeto, via SQLAlchemy), permitindo
manipular dados sem escrever SQL manualmente na maior parte do código.

**pgvector** — extensão do PostgreSQL que adiciona um tipo de dado `vector`
e operações de busca por similaridade vetorial.

**Prompt** — o texto de instrução enviado a um LLM. O `system_prompt`
(tabela `agents`) define a personalidade e as regras de comportamento do
agente de IA.

**Proxy reverso** — um servidor (aqui, o Nginx) que recebe requisições
externas e as repassa a um servidor interno, escondendo a estrutura real do
sistema e centralizando funções como HTTPS.

**RAG (Retrieval-Augmented Generation)** — técnica de buscar informação
relevante numa base de documentos antes de pedir a resposta a um LLM,
injetando essa informação como contexto no prompt (ver
[capítulo 2.6](./02-arquitetura.md)).

**Repository (padrão de projeto)** — uma classe que isola todas as queries
SQL relacionadas a uma tabela, para que o resto do código nunca escreva SQL
diretamente (ver `app/db/repositories/`).

**Schema (banco de dados)** — um "namespace" dentro de um banco Postgres
que agrupa tabelas; este projeto usa o schema `public` para suas próprias
tabelas, e coexiste com o schema `n8n`, usado internamente pelo n8n (ver
[capítulo 15.5](./15-n8n.md)). Não confundir com "schema" no sentido de
"estrutura de uma tabela".

**Session ID** — identificador único de uma conversa, no formato
`"provider:numero"` (ex: `"whatsapp_cloud:5511999999999"`), usado para
recuperar ou criar a conversa correta a cada mensagem recebida.

**Slug** — um identificador em formato amigável para URL, geralmente em
minúsculas e com hífens no lugar de espaços (ex: `alegra-brasil`).

**Stub** — uma implementação vazia ou mínima de uma interface, criada como
esqueleto para uma funcionalidade futura ainda não construída (ex:
`telegram_provider.py`).

**UUID (Universally Unique Identifier)** — um identificador de 128 bits,
praticamente impossível de colidir mesmo gerado de forma independente em
sistemas diferentes; usado como chave primária em todas as tabelas deste
projeto (ex: `f6081795-6aeb-4d82-894b-110840ed5d38`).

**Vetor** — uma lista ordenada de números, usada matematicamente para
representar o significado de um texto (ver "Embedding" acima).

**Webhook** — um mecanismo em que um sistema externo chama uma URL sua
automaticamente quando um evento acontece (ex: mensagem recebida), ao
contrário de você precisar consultar repetidamente se há algo novo (ver
[capítulo 10.2](./10-canais-de-mensagem.md)).

**WhatsApp Business Account (WABA)** — a conta comercial da Meta associada
a um ou mais números de telefone usados na WhatsApp Cloud API.
