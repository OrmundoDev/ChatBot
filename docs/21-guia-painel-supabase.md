# 21. Guia Rápido — Painel Administrativo (Supabase)

Este capítulo é o ponto de partida para quem for construir a interface
gráfica do painel. Ele assume que você já leu o
[capítulo 4 (Banco de Dados)](./04-banco-de-dados.md) para entender o
schema.

## Conexão

- **Project URL:** `https://jeqxkotopyiyevnbrpdv.supabase.co`
- **Anon key:** pegue em Project Settings → API, no dashboard do Supabase (é
  a chave pública, segura para embutir no frontend).

```bash
npm install @supabase/supabase-js
```

```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://jeqxkotopyiyevnbrpdv.supabase.co',
  'SUA_ANON_KEY_AQUI'
)
```

## Login

Use o Supabase Auth normalmente:
```javascript
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'operador@empresa.com',
  password: '...',
})
```

## Como criar um operador novo (procedimento manual, por enquanto)

Não existe uma tela de cadastro自动. Para cada operador novo:

1. Crie o usuário no dashboard do Supabase: **Authentication → Users → Add user**.
2. Vincule ele à empresa certa, rodando no SQL Editor:
```sql
UPDATE auth.users
SET raw_app_meta_data = raw_app_meta_data || jsonb_build_object('company_id', 'UUID_DA_EMPRESA')
WHERE email = 'email_do_operador@empresa.com';
```

Sem esse passo 2, o login funciona, mas todas as consultas retornam vazio —
é o `company_id` no `app_metadata` que a política de RLS usa para saber de
qual empresa são os dados que esse usuário pode ver.

## O que já está liberado via RLS (Row Level Security)

| Tabela | Operação liberada | Filtro |
|---|---|---|
| `companies` | SELECT | só a própria empresa |
| `agents` | SELECT | só agentes da própria empresa |
| `channels` | SELECT | só canais da própria empresa |
| `conversations` | SELECT, UPDATE | só conversas da própria empresa |
| `messages` | SELECT | só mensagens da própria empresa |
| `users`, `documents`, `chunks` | nenhuma ainda | RLS ligado, sem política — bloqueadas por enquanto |

Todas as consultas via SDK já vêm filtradas automaticamente pela política —
não precisa (mas também não tem problema) adicionar `.eq('company_id', ...)`
manualmente nas queries.

## Exemplo: listar conversas
```javascript
const { data, error } = await supabase
  .from('conversations')
  .select('id, session_id, status, created_at')
  .order('created_at', { ascending: false })
```

## Exemplo: pausar a IA numa conversa (assumir controle humano)
```javascript
await supabase
  .from('conversations')
  .update({ status: 'human_active' })
  .eq('id', conversationId)
```
Valores possíveis de `status`: `ai_active` (padrão, bot responde),
`human_active` (humano assumiu), `waiting_human` (aguardando humano).

## Exemplo: escutar mensagens novas em tempo real (Realtime)
```javascript
supabase
  .channel('mensagens-novas')
  .on(
    'postgres_changes',
    { event: 'INSERT', schema: 'public', table: 'messages' },
    (payload) => {
      console.log('Nova mensagem:', payload.new)
    }
  )
  .subscribe()
```
Só `conversations` e `messages` têm Realtime habilitado hoje.

## O que NÃO fazer

Não crie tabelas ou colunas novas direto pela interface do Supabase
(Table Editor) — qualquer mudança de schema deve ser uma migration nova do
Alembic (ver [capítulo 14](./14-deploy.md)), para manter tudo versionado no
Git. Se precisar de uma tabela/coluna nova para o painel, peça para o Bruno
criar a migration correspondente.
