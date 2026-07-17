# 13. Git

## 13.1 Onde o código vive

Repositório privado no GitHub: `git@github.com:OrmundoDev/ChatBot.git`. O
clone de trabalho vive **exclusivamente na VPS** — decisão deliberada deste
projeto: não há mais desenvolvimento local numa máquina pessoal, todo o
código-fonte e o ambiente de execução vivem no mesmo lugar (a VPS), evitando
divergência entre "onde eu programo" e "onde roda de verdade".

```bash
git remote -v
# origin  git@github.com:OrmundoDev/ChatBot.git (fetch)
# origin  git@github.com:OrmundoDev/ChatBot.git (push)
```

O acesso é via SSH (chave `deploy key` configurada na VPS, com permissão de
leitura e escrita).

## 13.2 Branches

```bash
git branch -a
#   remotes/origin/HEAD -> origin/main
#   remotes/origin/main
#   remotes/origin/refactor/core-architecture
```

Hoje existe efetivamente **uma branch ativa: `main`**. A branch
`refactor/core-architecture` foi usada durante a reescrita da arquitetura
para o modelo multi-tenant e já foi mergeada em `main` (fast-forward) — ela
continua existindo no remoto como histórico, mas não é mais usada para
trabalho ativo.

## 13.3 Histórico real de commits (referência)

```
aad5a4b feat: suporte a BSPs (ex: Datafy) via api_base_url configurável por canal
4f9daa1 fix: verificação de webhook do WhatsApp Cloud busca canal pelo verify_token no banco (suporte real a multi-tenant)
6d9f5af fix: ajusta dimensão do vetor no modelo ORM para 1536 (OpenAI text-embedding-3-small)
46d8b30 fix: usa gen_random_uuid() nativo do Postgres em vez da extensão uuid-ossp
cd7851c feat: adiciona provider OpenAI (chat + embeddings), remove dependência do Ollama como padrão
1b35028 feat: adiciona serviço backend ao docker-compose
4654de6 chore: adiciona Dockerfile do backend
8fbffc6 chore: adiciona .gitignore, ajustes no webhook Evolution e no script de ingestão, remove local antigo de knowledge_base
8fb78e7 etapa-2: schema multi-agente com Alembic, memoria real e controle de status
baebce8 config: migração para pydantic-settings + variáveis de canal
704d7ba checkpoint antes da Etapa 1 (refatoracao de arquitetura)
351843b feat: versao estavel
cc0d5bf feat: estrutura inicial do projeto de chatbot
```

Padrão de mensagem observado: prefixo (`feat:`, `fix:`, `chore:`, ou o nome
da etapa do roadmap) seguido de descrição objetiva do que mudou e, quando
relevante, por quê. Recomenda-se manter esse padrão daqui para frente —
facilita muito reconstruir a história de decisões técnicas do projeto (como
este próprio manual fez, lendo o log de commits).

## 13.4 Fluxo de trabalho recomendado

Como o projeto já está em produção e o desenvolvimento acontece direto na
VPS, o fluxo seguro é:

```bash
cd ~/chatbot-app
git status                    # confirme que não há mudanças não commitadas de outra sessão
git pull origin main          # traga qualquer mudança feita por outra pessoa/máquina
# ... editar arquivos ...
git add <arquivos alterados>  # evite "git add ." sem revisar — risco de commitar segredos
git status                    # confira o que está staged antes de commitar
git commit -m "tipo: descrição objetiva da mudança"
git push origin main
docker compose up -d --build backend   # aplica a mudança de fato (capítulo 9)
```

## 13.5 O que nunca deve ser commitado

O `.gitignore` já bloqueia isso, mas vale saber o porquê: `.env` (segredos
reais — senhas, chave da OpenAI, tokens), `venv/` e `__pycache__/` (gerados
localmente, não fazem sentido versionados), `knowledge_base/` (arquivos
reais de clientes — dados sensíveis de negócio, não código). Antes de um
push, em caso de dúvida:

```bash
git status                          # confirme o que está sendo enviado
git ls-files | grep -i "\.env\|secret\|token"   # busca por possíveis vazamentos já commitados
```

## 13.6 Conflitos e rollback

**Conflito de merge:** se `git pull` acusar conflito, o Git marca os
trechos conflitantes diretamente nos arquivos
(`<<<<<<<`, `=======`, `>>>>>>>`) — resolva manualmente, escolhendo/mesclando
o conteúdo correto, depois `git add` nos arquivos resolvidos e
`git commit` para finalizar o merge.

**Desfazer o último commit (ainda não enviado ao GitHub):**
```bash
git reset --soft HEAD~1   # desfaz o commit, mantém as mudanças nos arquivos
```

**Reverter um commit já enviado (sem apagar histórico):**
```bash
git revert <hash_do_commit>   # cria um novo commit que desfaz as mudanças daquele commit
```

**Voltar o código rodando para uma versão anterior sem mexer no Git:**
```bash
git checkout <hash_do_commit> -- .
docker compose up -d --build backend
# depois, para voltar ao normal:
git checkout main -- .
```
Rollback mais seguro em produção está detalhado no
[capítulo 14 (Deploy)](./14-deploy.md).
