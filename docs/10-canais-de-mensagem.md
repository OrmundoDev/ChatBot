# 10. Canais de Mensagem e Integrações

## 10.1 O conceito de "canal" no sistema

Um **canal** (tabela `channels`) é qualquer meio pelo qual uma mensagem
entra e sai do sistema. Hoje, na prática, isso sempre significa WhatsApp,
mas o desenho já suporta múltiplos canais por agente (e o código já tem
stubs — implementações vazias, só de estrutura — para Telegram, Instagram e
Web Chat). Toda a lógica específica de "como falar com esse canal" fica
isolada dentro de uma classe que implementa `ChannelProvider`
(`app/channels/base.py`) — o resto do sistema nunca lida diretamente com a
API do WhatsApp, só com esse contrato abstrato (ver
[capítulo 2.5](./02-arquitetura.md)).

## 10.2 O que é um webhook

Um **webhook** é o inverso de uma chamada de API normal: em vez do seu
sistema perguntar "tem mensagem nova?" repetidamente (*polling*), você
registra uma URL sua junto ao provedor (Meta, no caso do WhatsApp), e é o
**provedor quem chama essa URL** automaticamente, toda vez que algo
acontece (uma mensagem chega, por exemplo). Por isso o backend precisa
estar acessível publicamente via HTTPS (capítulo 14) — sem isso, a Meta não
consegue entregar nada.

## 10.3 WhatsApp Cloud API (Meta) — o canal de produção

É a API **oficial** da Meta para integração com WhatsApp Business. Ao
contrário de soluções não-oficiais, ela exige que o número passe por um
processo de verificação da Meta, mas em troca oferece estabilidade e não
corre risco de banimento por uso de engenharia reversa.

### Fluxo de configuração de um número (visão geral)

1. Criar um app no [developers.facebook.com](https://developers.facebook.com)
   (Meta for Developers), adicionar o produto WhatsApp.
2. Obter (ou gerar via um BSP, ver seção 10.5) três identificadores:
   `phone_number_id`, `waba_id` (WhatsApp Business Account ID) e
   `business_id`.
3. Gerar um token de acesso (`access_token`) — temporário (24h, para testes)
   ou permanente (via um System User da Meta, para produção).
4. Configurar a URL do webhook (`https://api.speedbot.space/webhooks/whatsapp_cloud`)
   e um `verify_token` de sua escolha, no painel da Meta (ou do BSP).
5. O número precisa ter `code_verification_status = VERIFIED` — sem isso,
   mensagens reais de usuários não são roteadas de fato pela Meta, mesmo que
   toda a configuração técnica esteja correta (ver
   [capítulo 18](./18-troubleshooting.md)).

### Verificação do webhook (GET)

Quando você configura a URL do webhook no painel da Meta, ela faz uma
chamada `GET` única, enviando três parâmetros de query string:
`hub.mode=subscribe`, `hub.verify_token=<o token que você escolheu>` e
`hub.challenge=<um número aleatório>`. Seu servidor precisa devolver
exatamente o valor de `hub.challenge` como resposta em texto puro, **se e
somente se** o `hub.verify_token` recebido bater com o que você configurou.
Código real (`app/api/webhooks/whatsapp_cloud.py`):

```python
@router.get("/whatsapp_cloud")
async def verify_whatsapp_cloud_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    params = dict(request.query_params)
    token = params.get("hub.verify_token")

    channel = (
        await ChannelRepository.get_by_verify_token(db, "whatsapp_cloud", token)
        if token else None
    )
    config = channel.config if channel else None

    provider = get_channel_provider("whatsapp_cloud", config=config)
    challenge = await provider.verify_webhook(params)

    if challenge:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Falha na verificação")
```

**Ponto importante de multi-tenant:** esse `GET` da Meta **não informa qual
`phone_number_id` está sendo configurado** — só o `verify_token`. Por isso
esse endpoint busca o canal pelo `verify_token` guardado em `config`
(`ChannelRepository.get_by_verify_token`), e não pelo identificador do
número. Isso significa que **cada canal precisa ter um `verify_token`
único** — se dois canais tivessem o mesmo valor, a busca no banco
(`.scalar_one_or_none()`) poderia ficar ambígua ou pegar o canal errado.

### Recebimento de mensagens (POST)

Toda mensagem recebida chega como um `POST` no mesmo endpoint. O payload
segue uma estrutura fixa da Meta:

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "changes": [{
      "value": {
        "metadata": { "phone_number_id": "570906922765104" },
        "messages": [{
          "from": "5511999999999",
          "id": "wamid.xxx",
          "type": "text",
          "text": { "body": "Olá, preciso de ajuda com meu pedido" }
        }]
      }
    }]
  }]
}
```

O backend extrai `metadata.phone_number_id` para achar o canal certo no
banco (`ChannelRepository.get_by_identifier`) — é isso que roteia a
mensagem para a empresa/agente correto. **O endpoint sempre responde `200
OK`**, mesmo em caso de erro interno (`try/except` amplo em
`receive_whatsapp_cloud_message`) — isso é proposital: a Meta trata qualquer
status diferente de `200` como falha de entrega e pode desativar o webhook
após falhas repetidas.

### Envio de mensagens

```python
url = f"{self.api_base}/{self.phone_number_id}/messages"
headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
payload = {
    "messaging_product": "whatsapp",
    "to": to_id,
    "type": "text",
    "text": {"body": content},
}
```

## 10.4 O campo `config` do canal — credenciais no banco, não no código

Cada canal guarda suas próprias credenciais na coluna `channels.config`
(JSONB). Para `whatsapp_cloud`:

```json
{
    "phone_number_id": "570906922765104",
    "access_token": "TOKEN_AQUI",
    "verify_token": "escolhido_por_voce",
    "api_base_url": "https://cloud.datafyapi.com.br/v1"
}
```

Isso é o que permite múltiplos clientes, cada um com seu próprio número e
credenciais, rodando na mesma instalação do sistema, sem editar `.env` nem
reiniciar nada a cada cliente novo — mudanças em `config` têm efeito
imediato na próxima mensagem recebida.

## 10.5 BSPs (Business Solution Providers) — o caso da Datafy

Um **BSP** é uma empresa homologada pela própria Meta que atua como
intermediária/proxy da WhatsApp Cloud API — ela repassa as chamadas para a
Meta e devolve a resposta sem alterar o formato, mas com sua própria URL e
seu próprio token. A vantagem prática de usar um BSP como a **Datafy** é
pular parte da burocracia de verificação de negócio própria da Meta.

`api_base_url` no `config` é a chave que resolve isso **sem duplicar
código**: se ausente, o sistema usa a Graph API oficial da Meta
(`https://graph.facebook.com/v19.0`, constante `GRAPH_API_BASE` em
`whatsapp_cloud_provider.py`); se presente, usa a URL do BSP. O restante do
fluxo (payload de envio, formato do webhook recebido) é idêntico, porque o
BSP homologado espelha fielmente o contrato da Meta — por isso nenhuma outra
parte do código precisou mudar para suportar a Datafy.

```python
self.api_base = cfg.get("api_base_url") or GRAPH_API_BASE
...
url = f"{self.api_base}/{self.phone_number_id}/messages"
```

### Endpoints úteis da Datafy usados neste projeto

```bash
# Descobrir phone_number_id, waba_id e business_id a partir do token
curl https://cloud.datafyapi.com.br/me --header 'Authorization: Bearer SEU_TOKEN'

# Consultar status de verificação de um número
curl "https://cloud.datafyapi.com.br/v1/{waba_id}/phone_numbers" \
  --header 'Authorization: Bearer SEU_TOKEN'

# Solicitar código de verificação do número (SMS ou ligação)
curl -X POST "https://cloud.datafyapi.com.br/v1/{phone_number_id}/request_code" \
  --header 'Authorization: Bearer SEU_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{"code_method":"SMS","language":"pt_BR"}'

# Confirmar o código recebido
curl -X POST "https://cloud.datafyapi.com.br/v1/{phone_number_id}/verify_code" \
  --header 'Authorization: Bearer SEU_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{"code":"CODIGO_RECEBIDO"}'

# Consultar números bloqueados nesse canal
curl "https://cloud.datafyapi.com.br/v1/{phone_number_id}/block_users" \
  --header 'Authorization: Bearer SEU_TOKEN'
```

O webhook em si (URL de entrega + eventos) é configurado **no próprio
painel da Datafy** (`app.datafyapi.com.br` → Webhooks), não no painel da
Meta — a Datafy repassa os eventos recebidos da Meta para a URL cadastrada
lá. Os eventos relevantes para este sistema são `messages` (mensagens
recebidas) e `smb_message_echoes` (ecos de mensagens enviadas via o app
nativo do WhatsApp Business, se o cliente também usar o app ao mesmo
tempo).

## 10.6 Evolution API — implementada, não usada em produção

A Evolution API é uma alternativa não-oficial: ela emula o WhatsApp Web
para enviar/receber mensagens, sem exigir aprovação da Meta. A vantagem é
não depender de burocracia de verificação; a desvantagem, e motivo de não
ser a escolha para clientes reais neste projeto, é o **risco de banimento
do número** pela Meta, por não ser uma via oficial.

O provider (`evolution_provider.py`) está implementado e funcional — pode
ser usado como canal caso um cliente prefira essa via assumindo o risco —
mas hoje nenhum cliente real está configurado com ela.

```json
{
    "api_url": "http://evolution_api:8080",
    "api_key": "sua_chave",
    "instance": "nome_da_instancia"
}
```

O webhook recebido tem formato próprio (`event: "messages.upsert"`,
diferente do formato da Meta), tratado em `POST /webhooks/evolution`
(`app/api/webhooks/evolution.py`) — endpoint independente do
`/webhooks/whatsapp_cloud`, que coexiste com o uso legado via n8n (ver
[capítulo 15](./15-n8n.md)) sem conflito.

## 10.7 Canais planejados, ainda não implementados

`telegram_provider.py`, `instagram_provider.py` e `webchat_provider.py`
existem como **stubs** — implementam a interface `ChannelProvider`, mas
todo método real lança `NotImplementedError`. Servem como esqueleto pronto
para quando esses canais forem priorizados; não fazem nada hoje.
