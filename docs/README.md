# Manual Oficial — Plataforma de Chatbot

Este é o manual técnico completo do projeto. Ele foi escrito para que qualquer
desenvolvedor — mesmo sem nenhum contato prévio com este projeto — consiga
assumir sua manutenção sem precisar perguntar nada ao desenvolvedor original.

Nenhum capítulo assume conhecimento prévio de nenhuma tecnologia. Se você já
conhece Docker, por exemplo, pode pular direto para a parte específica do
projeto dentro de cada capítulo — mas a explicação de base está sempre lá.

## Como usar este manual

Se você é novo no projeto, leia na ordem: capítulos 1 a 4 dão a visão geral e
a base de dados, que é o esqueleto de tudo. Os capítulos 5 a 8 explicam a
Base de Conhecimento (RAG). Os capítulos 9 a 15 são operação (Docker, canais,
backend, logs, git, deploy, n8n). O capítulo 16 documenta a API. O 17 amarra
tudo num fluxo único. Os capítulos 18 a 20 são referência (troubleshooting,
FAQ, glossário) — volte a eles sempre que precisar.

Se você já conhece o projeto e só quer resolver um problema pontual, vá direto
ao [capítulo 18 (Troubleshooting)](./18-troubleshooting.md) ou ao
[capítulo 20 (Glossário)](./20-glossario.md).

## Índice

1. [Visão Geral](./01-visao-geral.md)
2. [Arquitetura](./02-arquitetura.md)
3. [Estrutura de Pastas e Arquivos](./03-estrutura-pastas.md)
4. [Banco de Dados](./04-banco-de-dados.md)
5. [Base de Conhecimento (Knowledge Base)](./05-base-de-conhecimento.md)
6. [Chunking](./06-chunking.md)
7. [Embeddings](./07-embeddings.md)
8. [Processo de Ingestão](./08-processo-de-ingestao.md)
9. [Docker e Docker Compose](./09-docker.md)
10. [Canais de Mensagem e Integrações](./10-canais-de-mensagem.md)
11. [Backend](./11-backend.md)
12. [Logs](./12-logs.md)
13. [Git](./13-git.md)
14. [Deploy](./14-deploy.md)
15. [n8n](./15-n8n.md)
16. [API](./16-api.md)
17. [Fluxo Completo da Mensagem](./17-fluxo-completo-mensagem.md)
18. [Troubleshooting](./18-troubleshooting.md)
19. [FAQ](./19-faq.md)
20. [Glossário](./20-glossario.md)
21. [Guia Rápido — Painel Administrativo (Supabase)](./21-guia-painel-supabase.md)

## Estado do projeto no momento em que este manual foi escrito

- Backend rodando em produção na VPS (Contabo), atrás de Nginx com HTTPS
  (Let's Encrypt).
- Banco: PostgreSQL com extensão `pgvector`, hospedado no **Supabase**
  (migrado de um container Postgres local — ver
  [capítulo 4](./04-banco-de-dados.md) e
  [capítulo 21](./21-guia-painel-supabase.md)). O backend continua na VPS;
  só o banco de dados saiu de lá.
- **Row Level Security (RLS)** habilitado nas tabelas de negócio, preparando
  o terreno para o painel administrativo se conectar direto no Supabase —
  ver capítulo 4 (seção de RLS) e capítulo 21.
- IA: OpenAI (`gpt-5.4-mini` para chat, `text-embedding-3-small` para
  embeddings). Ollama continua implementado no código como opção futura, mas
  não está em uso.
- Canal de produção real: WhatsApp Cloud API via BSP (Datafy), para o
  primeiro cliente real. A Evolution API está implementada mas não é usada
  em produção.
- n8n está rodando na VPS (Postgres local, schemas próprios) mas fora do
  fluxo de produção (infraestrutura legada) — não foi migrado para o
  Supabase, propositalmente, para manter o escopo da migração mínimo.
- Painel administrativo: em construção por outro desenvolvedor, conectando
  direto ao Supabase (API + Realtime), com RLS já configurado como camada de
  isolamento entre empresas.
