# 18. Troubleshooting

Cada caso abaixo é um problema real já enfrentado e resolvido neste
projeto, documentado no formato: Problema → Como identificar → Causa →
Como resolver → Como evitar.

---

### `uuid_generate_v4() does not exist`

**Como identificar:** erro ao rodar `alembic upgrade head` pela primeira
vez, mencionando essa função especificamente.

**Causa:** a migration original tentava usar a extensão `uuid-ossp` para
gerar UUIDs, mas a imagem Docker `pgvector/pgvector:pg16` usada neste
projeto não expõe essa extensão corretamente, mesmo com
`CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` não acusando erro na hora de
criar a extensão em si.

**Como resolver:** trocar todo uso de `uuid_generate_v4()` pela função
nativa `gen_random_uuid()`, disponível no núcleo do Postgres desde a versão
13 (não depende de extensão nenhuma). Remover a linha de criação da
extensão `uuid-ossp`.

**Como evitar:** ao escrever DDL manual em migrations, preferir sempre
`gen_random_uuid()` a `uuid_generate_v4()` neste projeto, já que já está
comprovado que a imagem base usada não suporta a segunda de forma
confiável.

---

### `expected 1024 dimensions, not 1536`

**Como identificar:** erro do SQLAlchemy/pgvector ao rodar uma busca RAG
(`KnowledgeService.search`) ou uma ingestão, mencionando incompatibilidade
de dimensão do vetor.

**Causa:** existem **dois lugares diferentes** onde a dimensão do vetor é
declarada — a migration (`vector(1536)` na DDL) e o model ORM
(`Vector(1024)` em `app/db/models/chunk.py`). Ao trocar de modelo de
embedding (de Ollama `bge-m3`, 1024 dimensões, para OpenAI
`text-embedding-3-small`, 1536 dimensões), a migration foi ajustada mas o
model Python ficou com o valor antigo, e o SQLAlchemy valida a dimensão
usando o model, não o schema real do banco.

**Como resolver:** garantir que `Vector(N)` em `chunk.py` sempre bata
exatamente com o `vector(N)` da migration, e reconstruir o container depois
(`docker compose up -d --build backend`) — só editar o arquivo no disco não
basta (ver o próximo caso).

**Como evitar:** ao trocar de modelo de embedding, sempre buscar por todas
as ocorrências de `vector(` e `Vector(` no projeto
(`grep -rn "vector(\|Vector(" backend/`) antes de assumir que a mudança
está completa. Ver [capítulo 7.7](./07-embeddings.md).

---

### Editei o código mas a mudança não teve efeito

**Como identificar:** o comportamento continua igual ao anterior, mesmo
depois de editar o arquivo `.py` e reiniciar o container.

**Causa:** `docker compose restart` reinicia o **processo** dentro do
container, mas usa a **mesma imagem** já construída — que já tem o código
antigo "congelado" dentro dela (`COPY . .` no Dockerfile copia o código só
no momento do `build`). Editar o arquivo no disco da VPS não altera o que
está dentro da imagem já construída.

**Como resolver:** `docker compose up -d --build backend` — o `--build`
força a reconstrução da imagem, incorporando as mudanças de código.

**Como evitar:** internalizar a regra: qualquer mudança em `.py` dentro de
`backend/app/` ou `backend/scripts/` exige `--build` no comando de subida.
Só arquivos dentro do *bind mount* (`knowledge_base/`) refletem
mudanças sem rebuild.

---

### `Recipient phone number not in allowed list` (erro 131030)

**Como identificar:** erro retornado pela Graph API ao tentar enviar uma
mensagem, com esse código específico.

**Causa:** apps da Meta em modo Desenvolvimento (não publicados/verificados)
só podem enviar mensagens para números explicitamente cadastrados numa
lista de até 5 destinatários de teste, configurada no painel do app.

**Como resolver:** no painel do Meta for Developers, seção "Configuração da
API" → "Gerenciar lista de números de telefone", adicionar o número
destinatário.

**Como evitar:** esse limite só existe em apps não publicados — não afeta
números conectados via um BSP homologado já verificado (como a Datafy, para
clientes reais).

---

### Mensagens reais nunca chegam nos logs, só testes manuais via curl funcionam

**Como identificar:** enviar uma mensagem de verdade pelo celular não gera
nenhuma linha nova em `docker compose logs backend -f`, mas simular o
mesmo payload via `curl` funciona perfeitamente.

**Causa:** apps da Meta não publicados/não verificados só entregam webhooks
de **teste**, disparados manualmente pelo botão "Testar" do próprio painel
da Meta — trocas de mensagens reais entre usuários reais não geram webhook
nenhum nesse modo, independente de o número estar na lista de teste ou não.

**Como resolver:** publicar/verificar o app na Meta (processo de
verificação de negócio), ou usar um número conectado via BSP já homologado
(Datafy), que não sofre essa limitação de app em modo desenvolvimento.

**Como evitar:** para testes de desenvolvimento rápidos sem depender da
Meta de verdade, simular o payload via `curl` diretamente no endpoint é uma
estratégia válida e deliberada — só não confundir "funcionou no curl" com
"funciona com usuários reais" enquanto o app estiver em modo
desenvolvimento.

---

### Resposta não chega no celular, mas não aparece erro nenhum no log

**Como identificar:** o log mostra o fluxo completo rodando com sucesso
(`ConversationService TOTAL: ...s`), a chamada de envio não retorna erro,
mas a mensagem nunca aparece no WhatsApp do destinatário.

**Causa mais comum:** a janela de 24 horas de sessão de atendimento ao
cliente da WhatsApp Business Platform — mensagens de texto livre (fora de
template aprovado) só podem ser enviadas dentro de 24h após a **última
mensagem recebida de verdade daquele usuário através da rede da Meta**. Se
a mensagem "recebida" foi simulada via `curl` direto no seu servidor (sem
nunca passar pela rede da Meta), nenhuma janela de sessão real foi aberta
do lado da Meta — então o envio pode ser aceito pela API sem erro, mas
nunca chega ao aparelho.

**Como resolver:** garantir que a mensagem de entrada realmente transitou
pela rede da Meta (não foi simulada), ou usar um número já publicado/BSP
homologado sem essa limitação de modo desenvolvimento.

**Como evitar:** não confiar apenas em "a API não retornou erro" como prova
de entrega — validar a entrega de ponta a ponta com um número real, fora do
modo de simulação.

---

### Token de acesso expirado (24h)

**Como identificar:** chamadas de envio começam a falhar com erro de
autenticação depois de um dia funcionando normalmente.

**Causa:** tokens temporários da Meta expiram em 24h — comum em ambientes
de teste, antes de gerar um token permanente via System User.

**Como resolver:**
```sql
UPDATE channels
SET config = jsonb_set(config, '{access_token}', '"NOVO_TOKEN"')
WHERE id = 'UUID_DO_CANAL';
```
Efeito imediato, sem rebuild nem restart — validação prática da arquitetura
de credenciais no banco (capítulo 4).

**Como evitar:** para clientes reais em produção, gerar um token permanente
(via System User da Meta) em vez de depender do token temporário de 24h.

---

### Número com `code_verification_status: NOT_VERIFIED`

**Como identificar:**
```bash
curl "https://cloud.datafyapi.com.br/v1/{waba_id}/phone_numbers" --header 'Authorization: Bearer TOKEN'
```
mostra esse status no número em questão. Sintoma associado: testes de
webhook (disparados manualmente pelo painel) chegam normalmente (`200 OK`
nos logs), mas mensagens reais de usuários não geram nenhum evento.

**Causa:** a Meta exige que o número passe por verificação por código (SMS
ou ligação) antes de rotear mensagens reais de/para ele — isso é
independente e adicional à configuração de token/webhook, que pode estar
100% correta e mesmo assim não funcionar sem essa verificação.

**Como resolver:** solicitar o código (`request_code`) e confirmá-lo
(`verify_code`) — ver comandos completos no
[capítulo 10.5](./10-canais-de-mensagem.md). O código chega no número real
do cliente, não no seu — pode ser necessário coordenar esse passo com o
dono do número.

**Como evitar:** ao conectar um número novo, checar esse status **antes**
de assumir que tudo está pronto, mesmo que a criação do canal e do webhook
não tenham dado nenhum erro.

---

### Erro da Datafy: "Our servers are temporarily unavailable" ao solicitar código de verificação

**Como identificar:** `request_code` retorna erro (código 136024,
subcode 2388091), com `"is_transient": false` no corpo — apesar da mensagem
sugerir esperar 1 hora.

**Causa:** pode ser um rate-limit genuinamente temporário do lado da Meta,
**ou** um sintoma de que o Business Manager por trás daquela WABA ainda não
completou a verificação de negócio própria da Meta — nesse segundo caso,
esperar não resolve.

**Como resolver:** tentar novamente após o tempo sugerido; se persistir,
verificar o status de verificação de negócio no Business Manager
(business.facebook.com) ou contatar o suporte do BSP (Datafy), que lida com
esse tipo de caso rotineiramente.

**Como evitar:** não há prevenção garantida — é uma dependência externa da
infraestrutura da Meta. Vale sempre checar o Business Manager antes de
assumir que é puramente um rate-limit temporário.

---

### Um número específico não recebe resposta, mas todos os outros funcionam normalmente

**Como identificar:** múltiplos números de teste diferentes recebem
respostas corretamente; um número específico (frequentemente, o seu
próprio número pessoal, usado durante testes anteriores) nunca gera log
nenhum, mesmo mandando para o número certo.

**Causa real encontrada neste projeto:** o número pessoal estava cadastrado
como **número de teste** dentro de um app da Meta em modo Desenvolvimento
(usado em testes anteriores, de outro canal/empresa) — essa associação
interferiu na entrega de mensagens desse número específico para uma WABA
diferente e não relacionada.

**Como resolver:** no painel do Meta for Developers, no app usado para
testes, ir em WhatsApp → Configuração da API → lista de números de teste
("Para"), e **remover** o número pessoal de lá.

**Como evitar:** ao terminar uma fase de testes, limpar números de teste
que não serão mais usados dessa forma, evitando esse tipo de contaminação
cruzada em testes futuros com números reais de clientes.

---

### Consulta em `information_schema.columns` traz colunas duplicadas/estranhas de uma tabela

**Como identificar:** uma tabela como `agents` aparece com colunas
repetidas ou com nomenclatura inconsistente (`camelCase` misturado com
`snake_case`).

**Causa:** existe mais de uma tabela com o mesmo nome, em **schemas**
diferentes do mesmo banco (neste projeto: `public.agents`, do backend, e
`n8n.agents`, interno do n8n — ver [capítulo 15.5](./15-n8n.md)). Uma
consulta sem filtrar por `table_schema` mistura os resultados de ambas.

**Como resolver:** sempre incluir `table_schema` na consulta e/ou
qualificar explicitamente `public.` nas queries e no SQL de administração.

**Como evitar:** por hábito, escrever sempre `public.nome_da_tabela` em
qualquer SQL administrativo neste projeto, mesmo quando não estritamente
necessário.

---

### Nada aparece em `/var/log/nginx/access.log`, mas a Datafy diz que está tudo certo

**Como identificar:** o teste de webhook do painel da Datafy retorna sucesso
(e aparece `200 OK` no log do backend quando o teste é feito manualmente),
mas mensagens reais não geram nada, nem no Nginx.

**Causa neste caso:** não era um problema de infraestrutura (Nginx/firewall
já confirmados corretos) — era o número com `NOT_VERIFIED` (ver caso
específico acima). O teste manual do painel da Datafy dispara um evento
sintético direto para a URL cadastrada, sem depender do roteamento real de
mensagens da Meta — por isso "passa no teste" mesmo quando mensagens reais
não seriam entregues.

**Como evitar confundir os dois:** um teste de webhook bem-sucedido prova
que a URL, o Nginx e o backend estão corretos — **não prova** que o número
está apto a rotear mensagens reais. São duas validações independentes.

---

### `socket.gaierror: Name or service not known` ao conectar no Supabase, só de dentro do container

**Como identificar:** o mesmo hostname resolve normalmente via `getent hosts`
na VPS (fora do Docker), mas falha especificamente quando testado de dentro
do container do backend.

**Causa:** a conexão direta do Supabase (`db.<projeto>.supabase.co`) só tem
endereço **IPv6**. Containers Docker não têm IPv6 habilitado por padrão,
mesmo que o host (a VPS) tenha.

**Como resolver:** usar o **pooler em modo Session**
(`aws-0-<região>.pooler.supabase.com:5432`) em vez da conexão direta — ele
tem endereços IPv4, e ainda suporta prepared statements (diferente do
pooler em modo Transaction, que não suporta). Ver
[capítulo 4](./04-banco-de-dados.md).

**Como evitar:** antes de escolher o tipo de conexão de um Postgres externo
(Supabase ou qualquer outro provedor gerenciado), confirme se o host é
IPv4, IPv6, ou ambos — e lembre que "o host da VPS ter IPv6" não significa
que os containers Docker rodando nela também têm.

---

### Senha do banco com caractere especial quebra a conexão de forma silenciosa e confusa

**Como identificar:** erro de DNS (`Name or service not known`) ou de
autenticação mesmo com host e credenciais aparentemente corretos; o mesmo
comando funciona depois de trocar a senha por uma sem símbolos.

**Causa:** o `config.py` monta a URL de conexão colando usuário e senha
direto na string (`f"postgresql+asyncpg://{usuario}:{senha}@{host}..."`),
sem nenhum tratamento. Se a senha tiver um caractere especial de URL (`@`,
`/`, `#`, `%`), ele quebra a estrutura da URL — por exemplo, um `@` extra na
senha faz o parser interpretar um pedaço da própria senha como se fosse o
início do host, resultando num "host" sem sentido e, consequentemente, num
erro de DNS que nada tem a ver com DNS de verdade.

**Como resolver:** o `config.py` foi corrigido para usar
`urllib.parse.quote_plus()` no usuário e na senha antes de montar a URL —
isso já resolve para qualquer senha, com ou sem caractere especial.
Alternativamente (ou em conjunto), gerar uma senha só com letras e números
evita o problema por completo.

**Como evitar:** ao gerar credenciais novas para qualquer banco (Supabase ou
não), ou usar uma senha sem símbolos, ou garantir que o código que monta a
connection string sempre faça o *URL encoding* de usuário/senha.

---

### Arquivo criado por `alembic revision` "some" depois de reconstruir o container

**Como identificar:** você rodou `alembic revision -m "..."` dentro do
container, viu a mensagem de sucesso, mas o arquivo não aparece em
`backend/alembic/versions/` na VPS.

**Causa:** só a pasta `knowledge_base/` é *bind mount* no
`docker-compose.yml` — o resto de `/app` dentro do container (incluindo
`alembic/`) veio do `COPY . .` do Dockerfile, sem sincronia com o disco da
VPS. Um arquivo criado por um comando rodando **dentro** do container só
existe ali, na camada gravável do container — se ele for removido ou
reconstruído, o arquivo é perdido.

**Como resolver:** copiar o arquivo de dentro do container pra fora
imediatamente após gerá-lo:
```bash
docker compose cp backend:/app/alembic/versions/xxxx_nome.py backend/alembic/versions/xxxx_nome.py
```
E, depois de editar o conteúdo no disco da VPS, copiar de volta pra dentro
do container antes de aplicar a migration:
```bash
docker compose cp backend/alembic/versions/xxxx_nome.py backend:/app/alembic/versions/xxxx_nome.py
```

**Como evitar:** sempre que rodar `alembic revision` dentro do container,
copiar o arquivo gerado para a VPS **antes** de qualquer `docker compose up
--build`. Ver [capítulo 14](./14-deploy.md).

---

### Restauração de backup (`psql < arquivo.sql`) corrompe dados de tabelas que existiam antes de um erro

**Como identificar:** durante uma restauração, aparecem erros do tipo
`backslash commands are restricted; only \unrestrict is allowed` misturados
com `syntax error at or near "<uuid>"` — mesmo para tabelas que tinham sido
criadas com sucesso.

**Causa:** versões recentes do `pg_dump`/`psql` (a partir de uma atualização
de segurança) adicionam um par `\restrict <token>` / `\unrestrict <token>`
no início/fim do arquivo de dump. Em alguns cenários, esse modo restrito
interfere na leitura dos blocos `COPY ... FROM stdin`, fazendo o `psql`
tentar interpretar linhas de dado puro como comandos SQL.

**Como resolver:** remover as duas linhas (`\restrict` e `\unrestrict`) do
arquivo antes de restaurar:
```bash
sed -e '/^\\restrict/d' -e '/^\\unrestrict/d' arquivo.sql > arquivo_limpo.sql
```
Depois, restaurar com `-v ON_ERROR_STOP=1` para que qualquer problema real
pare a execução imediatamente, em vez de gerar uma cascata de erros
confusos.

**Como evitar:** ao gerar um dump com uma versão recente do `pg_dump`,
sempre inspecionar as primeiras e últimas linhas do arquivo
(`head`/`tail`) antes de restaurar, e remover esse par de linhas
preventivamente se identificado.
