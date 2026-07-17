# 19. FAQ

**Como eu cadastro um cliente novo do zero?**
Ver [capítulo 4.6](./04-banco-de-dados.md) (SQL de criação) e
[capítulo 8](./08-processo-de-ingestao.md) (alimentar a base de
conhecimento dele). Resumo: um `INSERT` encadeado criando empresa → agente
→ canal, depois rodar o script de ingestão apontando para a pasta de
documentos daquela empresa.

**Onde ficam as senhas e chaves de API?**
No arquivo `backend/.env`, na VPS — nunca no código, nunca no Git. Para
credenciais específicas de cada cliente (token do WhatsApp), ficam no banco,
na coluna `channels.config` (ver [capítulo 4.3](./04-banco-de-dados.md)).

**Por que existe suporte a Ollama no código se não está sendo usado?**
Foi mantido propositalmente como opção para uma futura migração a um
servidor de IA próprio (self-hosted), evitando dependência exclusiva da
OpenAI a longo prazo. Trocar de volta é só mudar `llm_provider` para
`"ollama"` na tabela `agents` daquele cliente específico — a arquitetura de
factory (capítulo 2) já suporta isso sem mudança de código.

**Por que existe suporte a Evolution API se o cliente real usa WhatsApp
Cloud API?**
Foi a primeira via de integração implementada, e continua funcional como
alternativa para um cliente que aceite o risco de uma via não-oficial. Não é
usada hoje por nenhum cliente real (ver [capítulo 10.6](./10-canais-de-mensagem.md)).

**Existe painel administrativo?**
Não. Todo o gerenciamento de clientes é feito hoje via SQL direto (DBeaver
ou `psql`). A tabela `users` existe no schema, preparada para um futuro
painel, mas sem nenhuma rota de API ou autenticação implementada em cima
dela.

**Como eu pauso a IA numa conversa específica (para um humano assumir)?**
```sql
UPDATE conversations SET status = 'human_active' WHERE session_id = 'whatsapp_cloud:NUMERO';
```
Ver [capítulo 4.3](./04-banco-de-dados.md).

**A IA "vê" documentos de outro cliente por engano?**
Não deveria — o isolamento é garantido pelo filtro `company_id` em toda
busca RAG (ver [capítulo 2.4](./02-arquitetura.md)), e já foi testado
deliberadamente com sucesso usando fatos-canário fictícios em duas empresas
de teste. Não existe, porém, Row-Level Security no nível do Postgres — o
isolamento depende inteiramente do código da aplicação sempre filtrar
corretamente. Qualquer nova query que toque em `chunks` ou `documents`
precisa manter esse filtro.

**Preciso reiniciar o backend depois de cadastrar um cliente novo no
banco?**
Não. Mudanças no banco (novo cliente, nova credencial, novo prompt) têm
efeito imediato na próxima mensagem processada. Reiniciar/reconstruir só é
necessário para mudanças de **código**.

**Como sei se uma mensagem de teste realmente validaria entrega real, ou
se é só um teste sintético?**
Ver [capítulo 18](./18-troubleshooting.md), casos sobre o modo
Desenvolvimento da Meta e sobre testes de webhook da Datafy — um teste de
webhook bem-sucedido não garante que mensagens reais de usuários sejam
roteadas.

**Existem testes automatizados?**
Não. Toda validação até agora foi manual (mensagens reais, consultas diretas
no banco). Adicionar testes automatizados (`pytest`) é uma melhoria futura
identificada, fora do escopo deste MVP.

**Como faço backup do banco antes de uma mudança arriscada?**
Ver [capítulo 4.9](./04-banco-de-dados.md) e
[capítulo 14.8](./14-deploy.md).

**O que fazer se eu esquecer de rodar `--build` depois de editar código?**
A mudança simplesmente não vai aparecer, sem nenhum erro — ver o caso
correspondente no [capítulo 18](./18-troubleshooting.md).
