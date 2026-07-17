# 12. Logs

## 12.1 Onde encontrar cada log

| O quê | Onde | Comando |
|---|---|---|
| Backend (aplicação) | Dentro do Docker | `docker compose logs backend -f` |
| Postgres | Dentro do Docker | `docker compose logs postgres -f` |
| Evolution API | Dentro do Docker | `docker compose logs evolution_api -f` |
| n8n | Dentro do Docker | `docker compose logs n8n -f` |
| Nginx (acesso) | Arquivo no host | `sudo tail -f /var/log/nginx/access.log` |
| Nginx (erros) | Arquivo no host | `sudo tail -f /var/log/nginx/error.log` |
| Sistema (SSH, firewall) | journalctl | `sudo journalctl -f` |

Um ponto que já gerou confusão real durante o desenvolvimento: se o site
tivesse uma diretiva `access_log` customizada no arquivo de configuração do
Nginx (`/etc/nginx/sites-available/<dominio>`), os logs desse domínio
específico ficariam em outro arquivo, diferente do `access.log` padrão.
**Sempre confira** o `cat` da configuração do site
(`/etc/nginx/sites-available/api.speedbot.space`) antes de assumir onde os
logs estão — no caso deste projeto, hoje não há customização, então o
`access.log` padrão cobre tudo, mas isso pode mudar se o Nginx for
reconfigurado.

## 12.2 Como ler os logs do backend — o que cada linha significa

O `ConversationService` e os services que ele chama imprimem logs
estruturados a cada etapa do processamento de uma mensagem (ver
[capítulo 17](./17-fluxo-completo-mensagem.md) para o fluxo completo). Uma
sequência de sucesso típica:

```
[ConversationService] Canal: whatsapp_cloud | Sessão: whatsapp_cloud:5511932971861
[KnowledgeService] 2 chunks encontrados em 0.75s (company=20875ea6-98aa-4833-8486-bf197ebafab8)
[HistoryService] 3 mensagens carregadas em 0.01s
[HistoryService] Salvo em 0.02s
[ConversationService] TOTAL: 1.59s
INFO:     172.18.0.1:48780 - "POST /webhooks/whatsapp_cloud HTTP/1.0" 200 OK
```

Interpretação linha a linha: a primeira linha confirma qual canal e qual
sessão (número) está sendo processada — útil para conferir, num sistema
multi-tenant, que a mensagem caiu na empresa/conversa certa. A linha do
`KnowledgeService` mostra quantos chunks a busca RAG encontrou e quanto
tempo levou — `0 chunks encontrados` é esperado para uma empresa sem
documentos ingeridos ainda, não é erro. `HistoryService` mostra quantas
mensagens de histórico foram carregadas (memória da conversa) e confirma o
salvamento da nova interação. `TOTAL` é o tempo fim-a-fim de todo o
processamento daquela mensagem — útil para identificar lentidão (ex: se
`TOTAL` estiver muito mais alto que a soma das etapas, o gargalo está na
chamada à IA em si, que não é logada individualmente hoje). A última linha
(`INFO: ... 200 OK`) é o log padrão do Uvicorn confirmando que a requisição
HTTP foi respondida com sucesso.

## 12.3 Ruído esperado (não é problema)

Servidores públicos recebem tráfego constante de bots automatizados
varrendo a internet em busca de vulnerabilidades comuns — isso aparece nos
logs como uma sequência de `404 Not Found` para caminhos aleatórios que
nunca existiram no projeto:

```
INFO:     172.18.0.1:57838 - "GET /js/twint_ch.js HTTP/1.0" 404 Not Found
INFO:     172.18.0.1:57854 - "GET /static/style/protect/index.js HTTP/1.0" 404 Not Found
```

Isso é normal e esperado em qualquer servidor exposto à internet — o
`404` correto já é a resposta certa (nega a existência do recurso sem
expor informação nenhuma). Não requer ação.

## 12.4 Como identificar um problema real nos logs

O padrão de investigação usado neste projeto, do mais externo para o mais
interno:

1. **A mensagem chegou no Nginx?** — `sudo tail -f /var/log/nginx/access.log`
   enquanto reproduz o problema. Se nada aparecer, o problema está antes do
   seu servidor (provedor do WhatsApp/BSP não está enviando).
2. **A mensagem chegou no backend?** — `docker compose logs backend -f`. Se
   aparecer no Nginx mas não aqui, o problema é entre o Nginx e o container
   (proxy mal configurado, container fora do ar).
3. **O processamento completou?** — procure a sequência de logs da seção
   12.2 até a linha final `200 OK`. Se parar no meio (ex: só apareceu
   `[ConversationService] Canal: ...` e nada depois), o erro está na etapa
   seguinte — normalmente uma exceção capturada silenciosamente (o
   `try/except` dos webhooks sempre retorna `200 OK` para a Meta mesmo em
   erro interno, então **ausência de erro visível não significa sucesso** —
   é preciso olhar se a sequência completa de logs apareceu).
4. **Teste isolado da causa suspeita** — ex: rodar o `curl` de consulta de
   status de número (capítulo 10) diretamente, sem depender do fluxo
   completo, para isolar se o problema é do lado do provedor de WhatsApp ou
   do próprio sistema.

Ver [capítulo 18 (Troubleshooting)](./18-troubleshooting.md) para os casos
reais já resolvidos usando exatamente esse método.
