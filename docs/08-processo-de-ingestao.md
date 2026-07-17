# 8. Processo de Ingestão

## 8.1 O que o script faz, passo a passo

`scripts/ingest_documents.py` é o script que transforma arquivos brutos
(PDF/TXT) em chunks pesquisáveis no banco. Para cada arquivo encontrado:

1. Verifica se aquele arquivo (mesmo nome, mesma empresa) já foi processado
   antes — se sim, pula (a menos que `--forcar` seja usado).
2. Extrai o texto (via `pypdf` para PDF, leitura direta para TXT).
3. Cria um registro em `documents` (tabela do banco) para representar esse
   arquivo.
4. Divide o texto em chunks (`chunking_service.py`, capítulo 6).
5. Para cada chunk, gera o embedding (`embedding_service.py`, capítulo 7) e
   salva em `chunks`, vinculado ao `document_id`, `company_id` e `agent_id`.
6. Só faz o `commit` final depois que **todos** os chunks foram processados
   com sucesso — se algo falhar no meio, nada daquele documento é salvo
   (evita documento "pela metade" no banco).

## 8.2 Como rodar

O script roda **dentro do container do backend** (ele precisa acessar o
banco e a API da OpenAI usando a mesma configuração do `.env`):

```bash
docker compose exec backend python -m scripts.ingest_documents \
  --company-id UUID_DA_EMPRESA \
  --agent-id UUID_DO_AGENTE \
  --pasta nome-da-pasta-dentro-de-knowledge_base/documents
```

Isso processa **todos** os arquivos dentro de
`backend/knowledge_base/documents/<nome-da-pasta>/`.

## 8.3 Todos os argumentos

| Argumento | Obrigatório | Para quê |
|---|---|---|
| `--company-id` | Sim | UUID da empresa dona dos documentos |
| `--agent-id` | Sim | UUID do agente associado |
| `--pasta` | Não (padrão: `default`) | Nome da subpasta dentro de `knowledge_base/documents/` |
| `--file` | Não | Processa **um único arquivo** específico, ignorando `--pasta` |
| `--forcar` | Não (flag, sem valor) | Reprocessa mesmo se já existir um documento com aquele nome para aquela empresa |

## 8.4 Exemplo real usado no desenvolvimento

Criação do documento de teste e ingestão (empresa de teste "empresa-b",
usada para validar isolamento entre clientes):

```bash
mkdir -p ~/chatbot-app/backend/knowledge_base/documents/teste-empresa-b

cat > ~/chatbot-app/backend/knowledge_base/documents/teste-empresa-b/plano_teste_b.txt << 'EOF'
Informações sobre o Plano Especial DataFy-Y77:
Este é um plano experimental usado exclusivamente para testes de isolamento entre empresas.
A taxa de adesão deste plano é de exatamente R$ 9.999,00.
O prazo de ativação é de 12 dias úteis.
O código de referência interno deste plano é QW-3301.
EOF

docker compose exec backend python -m scripts.ingest_documents \
  --company-id ID_DA_EMPRESA_B \
  --agent-id ID_DO_AGENTE_B \
  --pasta teste-empresa-b
```

Esse padrão (um "fato-canário": um dado inventado, que só pode vir daquele
documento específico, nunca do conhecimento geral da IA) foi usado
deliberadamente para provar duas coisas ao mesmo tempo: que o RAG está
funcionando de fato (a IA "sabe" o valor R$ 9.999,00 e o código QW-3301
mesmo sendo um dado inexistente na realidade) e que o isolamento entre
empresas é real (uma empresa diferente, perguntada sobre o mesmo plano,
corretamente nega conhecimento sobre ele).

## 8.5 Saída esperada no terminal (sucesso)

```
🚀 Iniciando ingestão
   Empresa:  <uuid>
   Agente:   <uuid>
   Pasta:    /app/knowledge_base/documents/teste-empresa-b
   Arquivos: 1 encontrado(s)
   Forçar:   não (pula duplicados)
──────────────────────────────────────────────────

📄 Processando: plano_teste_b.txt
  📝 312 caracteres extraídos
  🔪 1 chunk(s) gerado(s)
  🗂️  Documento registrado: <uuid>
  ✅ Chunk 1/1 processado
  ✅ Concluído: plano_teste_b.txt (1 chunks salvos)

──────────────────────────────────────────────────

📊 Resumo:
   ✅ Processados: 1
   ⏭️  Pulados:     0
   ❌ Erros:       0
```

## 8.6 Como validar que a ingestão funcionou de verdade

Não basta ver "sucesso" no terminal — o teste real é perguntar pelo
WhatsApp algo que só pode ser respondido usando aquele documento
específico, e conferir se a resposta bate. Também é possível conferir
diretamente no banco:

```sql
SELECT d.name, COUNT(c.id) AS total_chunks
FROM documents d
LEFT JOIN chunks c ON c.document_id = d.id
WHERE d.company_id = 'UUID_DA_EMPRESA'
GROUP BY d.name;
```

## 8.7 Erros comuns

| Erro | Causa | Solução |
|---|---|---|
| `❌ Pasta não encontrada` | A pasta `--pasta` não existe em `knowledge_base/documents/` | Criar a pasta com `mkdir -p` antes de rodar |
| `⚠️ Nenhum arquivo encontrado` | Pasta existe mas está vazia | Colocar os arquivos PDF/TXT lá antes |
| `⏭️ Já processado anteriormente` | Mesmo nome de arquivo já ingerido para essa empresa | Usar `--forcar`, ou apagar o registro antigo primeiro (capítulo 5.6) se for realmente uma atualização de conteúdo |
| `❌ Texto vazio ou não extraído` | PDF escaneado (imagem, sem texto real) ou arquivo corrompido | Converter para texto (OCR) fora do sistema antes de ingerir |
| `❌ UUID inválido` | `--company-id` ou `--agent-id` digitado errado | Conferir os UUIDs reais via `SELECT id FROM companies` / `SELECT id FROM agents` |
| Erro de dimensão do vetor (`expected N dimensions, not M`) | `EMBEDDING_MODEL` foi trocado sem reprocessar os chunks antigos | Ver [capítulo 18, Troubleshooting](./18-troubleshooting.md) |
