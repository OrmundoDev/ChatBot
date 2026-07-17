# 5. Base de Conhecimento (Knowledge Base)

## 5.1 O que é

É o conjunto de documentos reais de cada empresa (contratos-modelo, tabelas
de preço, políticas de atendimento, perguntas frequentes, etc.) que a IA usa
como fonte de verdade ao responder. Sem isso, a IA responderia só com
conhecimento genérico — a Base de Conhecimento é o que faz o chatbot "saber"
as regras específicas daquela empresa.

## 5.2 Como funciona, em alto nível

1. Você coloca os arquivos (PDF ou TXT) numa pasta específica da empresa, no
   disco da VPS.
2. Você roda o script `ingest_documents.py` (capítulo 8), que lê cada
   arquivo, quebra o texto em pedaços menores (chunking, capítulo 6), gera
   um vetor numérico para cada pedaço (embedding, capítulo 7) e salva tudo
   no banco.
3. A partir daí, toda pergunta recebida pelo WhatsApp passa por uma busca
   nesses vetores antes de ir para a IA — só os pedaços mais relevantes para
   aquela pergunta específica são enviados como contexto.

## 5.3 Onde fica no disco

```
backend/knowledge_base/documents/<pasta-da-empresa>/arquivo.pdf
backend/knowledge_base/documents/<pasta-da-empresa>/arquivo2.txt
```

Essa pasta **não é commitada no Git** (está no `.gitignore`) e é montada
como *bind mount* no `docker-compose.yml` — ou seja, os arquivos vivem
diretamente no disco da VPS, fora da imagem Docker, e continuam existindo
mesmo se o container for recriado (`docker compose up --build`).

`<pasta-da-empresa>` é escolhida por você, livremente, no momento em que
roda o script (parâmetro `--pasta`) — na prática, temos usado o mesmo texto
do `slug` da empresa cadastrado no banco (ver
[capítulo 4](./04-banco-de-dados.md)), por consistência, mas o script não
impõe essa regra automaticamente hoje.

## 5.4 Formatos aceitos

Hoje o script de ingestão (`extrair_texto`, em `ingest_documents.py`) só
sabe processar dois formatos:

| Extensão | Como o texto é extraído |
|---|---|
| `.pdf` | Biblioteca `pypdf`, página por página, concatenando o texto de todas |
| `.txt` | Lido diretamente como texto puro (UTF-8) |

Qualquer outro formato (`.docx`, imagens, planilhas) é **ignorado** com um
aviso no terminal — não gera erro, mas também não é processado.

## 5.5 Boas práticas de organização

- Um arquivo por assunto/tópico, em vez de um único arquivo gigante com tudo
  misturado — isso melhora a qualidade da busca, porque o chunking (capítulo
  6) corta por tamanho de caracteres, não por assunto; documentos bem
  segmentados naturalmente geram chunks mais coerentes.
- Nomes de arquivo descritivos (`politica-de-reembolso.txt` em vez de
  `documento1.txt`) — o nome do arquivo é salvo em `documents.name` e ajuda
  na hora de auditar o que já foi ingerido.
- PDFs escaneados como imagem (sem texto selecionável) **não funcionam** —
  o `pypdf` só extrai texto que já existe digitalmente no arquivo. Se um
  documento do cliente for um scan, ele precisa ser convertido para texto
  antes (OCR) ou reescrito como TXT manualmente.

## 5.6 Adicionar, atualizar e excluir documentos

**Adicionar:** coloque o arquivo novo na pasta da empresa e rode o script de
ingestão normalmente (capítulo 8) — ele processa só o que ainda não foi
processado (checagem por nome de arquivo + empresa).

**Atualizar um documento existente:** o script, por padrão, **pula**
arquivos já processados (mesmo nome + mesma empresa). Para reprocessar um
arquivo que mudou de conteúdo, use a flag `--forcar`:

```bash
docker compose exec backend python -m scripts.ingest_documents \
  --company-id UUID_DA_EMPRESA \
  --agent-id UUID_DO_AGENTE \
  --pasta nome-da-pasta \
  --forcar
```

Atenção: `--forcar` gera **novos** registros em `documents` e `chunks` — não
apaga os antigos automaticamente (o script não tem lógica de "substituir",
só de "criar de novo"). Isso significa que, hoje, atualizar um documento sem
apagar manualmente os chunks antigos deixa conteúdo duplicado/desatualizado
no banco, que pode ser retornado pela busca RAG junto com o novo. Para uma
atualização limpa, apague antes:

```sql
DELETE FROM chunks WHERE document_id = (
    SELECT id FROM documents WHERE company_id = 'UUID_DA_EMPRESA' AND name = 'nome_do_arquivo.txt'
);
DELETE FROM documents WHERE company_id = 'UUID_DA_EMPRESA' AND name = 'nome_do_arquivo.txt';
```
E rode a ingestão normalmente depois (sem precisar de `--forcar`, já que o
registro antigo não existe mais).

**Excluir um documento:** mesmo comando `DELETE` acima. Como
`chunks.document_id` tem `ON DELETE CASCADE`, apagar o `document` também
apagaria os chunks automaticamente — mas o `DELETE` explícito em `chunks`
primeiro (como no exemplo) é mais seguro e explícito sobre o que está sendo
feito.

## 5.7 Quando fazer ingestão, e quando não fazer

**Fazer:** sempre que o conteúdo real dos serviços/regras de um cliente
mudar (novo produto/serviço, novo valor de taxa, prazo alterado). **Não
fazer:** para mudanças de comportamento/tom do agente — isso é
responsabilidade do `system_prompt` (tabela `agents`, capítulo 4), não da
Base de Conhecimento. A Base de Conhecimento é sobre **fatos**; o
`system_prompt` é sobre **personalidade e regras de conduta**.
