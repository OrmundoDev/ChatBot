# 16. API

## 16.1 Documentação automática

O FastAPI gera documentação interativa automaticamente a partir do código —
não precisa ser escrita/mantida manualmente à parte:

```
https://api.speedbot.space/docs       # Swagger UI (interativo, testável no navegador)
https://api.speedbot.space/redoc      # ReDoc (leitura)
https://api.speedbot.space/openapi.json  # especificação crua, em JSON
```

Este capítulo é um retrato desses endpoints no momento em que este manual
foi escrito — a fonte de verdade sempre atualizada é o `/docs` ao vivo.

## 16.2 `GET /`

**Objetivo:** verificação simples de que a API está no ar. **Autenticação:**
nenhuma. **Parâmetros:** nenhum.

Resposta:
```json
{
  "mensagem": "API do Chatbot está no ar",
  "status": "ok",
  "version": "0.4.0"
}
```

## 16.3 `GET /health`

**Objetivo:** health check para monitoramento externo (ex: uptime
monitors). **Autenticação:** nenhuma. Não consulta o banco — só confirma
que o processo Python está respondendo.

Resposta:
```json
{
  "status": "healthy",
  "timestamp": "2026-07-16T14:32:01.123456"
}
```

## 16.4 `POST /chat`

**Objetivo:** endpoint de compatibilidade com o fluxo antigo via n8n (ver
[capítulo 15](./15-n8n.md)). Usa sempre o **primeiro agente ativo
encontrado no banco** (`AgentRepository.get_default`) — não diferencia
clientes. **Autenticação:** nenhuma (ponto de atenção — ver
[capítulo 18](./18-troubleshooting.md) sobre riscos).

Corpo da requisição:
```json
{ "pergunta": "Quais são os planos disponíveis?" }
```

Resposta (200):
```json
{ "resposta": "Temos os planos Básico, Padrão e Premium. Cada um..." }
```

Erro de validação (422) — se `pergunta` estiver ausente ou vazia:
```json
{
  "detail": [
    { "loc": ["body", "pergunta"], "msg": "String should have at least 1 character", "type": "string_too_short" }
  ]
}
```

## 16.5 `GET /webhooks/whatsapp_cloud`

**Objetivo:** verificação do webhook pela Meta (ou BSP) — chamado uma vez,
quando o webhook é configurado no painel. Ver
[capítulo 10.3](./10-canais-de-mensagem.md) para o funcionamento completo.

Parâmetros de query: `hub.mode`, `hub.verify_token`, `hub.challenge`.

Resposta em sucesso: o valor de `hub.challenge`, como texto puro (não
JSON). Resposta em falha: `403 Forbidden`.

## 16.6 `POST /webhooks/whatsapp_cloud`

**Objetivo:** receber mensagens reais de usuários via WhatsApp Cloud API
(Meta ou BSP). Ver [capítulo 10.3](./10-canais-de-mensagem.md) para o
payload completo e o funcionamento interno. **Sempre responde `200 OK`**,
mesmo em erro interno — comportamento proposital, exigido pela Meta.

## 16.7 `POST /webhooks/evolution`

**Objetivo:** receber mensagens via Evolution API, como alternativa direta
ao fluxo via n8n. Ver [capítulo 10.6](./10-canais-de-mensagem.md).

## 16.8 Endpoints planejados, ainda não implementados

A pasta `app/api/routes/` existe na estrutura do projeto mas está vazia —
reservada para uma futura API REST de administração (CRUD de empresas,
agentes, canais, documentos via HTTP, em vez de SQL direto). Hoje toda
operação administrativa é feita via banco de dados diretamente (capítulos
4, 5 e 8).
