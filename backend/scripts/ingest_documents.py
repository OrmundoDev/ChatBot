"""
Script de ingestão de documentos para o Knowledge Base.

Uso básico (processa todos os arquivos de uma empresa):
    python -m scripts.ingest_documents \\
        --company-id f358492c-880a-42a2-9f17-14db01deca51 \\
        --agent-id   77f2a927-d1e9-46ec-ab18-0a7903dc4cdc

Uso avançado (processa um arquivo específico):
    python -m scripts.ingest_documents \\
        --company-id f358492c-880a-42a2-9f17-14db01deca51 \\
        --agent-id   77f2a927-d1e9-46ec-ab18-0a7903dc4cdc \\
        --file backend/knowledge_base/documents/default/meu_arquivo.pdf

Formatos aceitos: .pdf, .txt e .md.
Arquivos .md têm o frontmatter YAML (bloco "--- ... ---" no topo,
se existir) removido automaticamente, e são divididos em chunks por
seção (títulos ## ou ###) em vez de corte cego por caractere — ver
chunking_service.py.

Como funciona:
1. Busca os arquivos da pasta da empresa (ou o arquivo especificado)
2. Para cada arquivo:
   a. Se já existir um documento com o mesmo nome para essa empresa,
      apaga ele e seus chunks antigos (cascade) ANTES de reprocessar —
      isso garante que rodar o script de novo nunca duplica conteúdo,
      e sempre reflete o estado atual do arquivo em disco.
   b. Cria um novo registro na tabela 'documents'
   c. Extrai o texto (PDF, TXT ou MD)
   d. Divide em chunks (por seção se for MD, por caractere se não)
   e. Gera embedding para cada chunk
   f. Salva na tabela 'chunks' com company_id e agent_id
3. O KnowledgeService já filtra por company_id nas buscas RAG

Importante: a substituição é sempre escopada por company_id — rodar
este script para uma empresa nunca apaga nem afeta documentos de
outra empresa.
"""

import asyncio
import argparse
import re
from pathlib import Path
from uuid import UUID

from pypdf import PdfReader
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models.document import Document
from app.services.embedding_service import gerar_embedding
from app.services.chunking_service import dividir_em_chunks

# Pasta raiz dos documentos — organizada por slug da empresa
PASTA_KNOWLEDGE_BASE = (
    Path(__file__).resolve().parent.parent / "knowledge_base" / "documents"
)


def extrair_texto_pdf(caminho: Path) -> str:
    """Extrai todo o texto de um arquivo PDF."""
    leitor = PdfReader(str(caminho))
    paginas = [pagina.extract_text() or "" for pagina in leitor.pages]
    return "\n".join(paginas)


def extrair_texto_md(caminho: Path) -> str:
    """
    Extrai o texto de um arquivo Markdown, removendo o frontmatter
    YAML do topo (bloco "--- ... ---"), se existir. O resto do
    Markdown (títulos, tabelas, listas) é mantido intacto — é usado
    pelo chunking por seção em chunking_service.py.
    """
    texto = caminho.read_text(encoding="utf-8")
    texto = re.sub(r'^---\s*\n.*?\n---\s*\n', '', texto, count=1, flags=re.DOTALL)
    return texto


def extrair_texto(caminho: Path) -> str | None:
    """
    Extrai texto do arquivo baseado na extensão.
    Retorna None se o formato não for suportado.
    """
    sufixo = caminho.suffix.lower()

    if sufixo == ".pdf":
        return extrair_texto_pdf(caminho)
    elif sufixo == ".txt":
        return caminho.read_text(encoding="utf-8")
    elif sufixo == ".md":
        return extrair_texto_md(caminho)
    else:
        print(f"  ⚠️  Formato não suportado, ignorando: {caminho.name}")
        return None


async def apagar_versao_anterior(
    sessao,
    company_id: UUID,
    nome_arquivo: str,
) -> int:
    """
    Apaga qualquer documento existente com esse nome, para essa empresa,
    e seus chunks (via ON DELETE CASCADE em chunks.document_id — não
    precisa apagar os chunks manualmente, o Postgres cuida disso).

    Escopado por company_id: nunca toca em documentos de outra empresa,
    mesmo que exista um arquivo de mesmo nome lá.

    Retorna quantos documentos antigos foram apagados (0 = nenhum,
    ou seja, primeira vez que esse arquivo é processado).
    """
    resultado = await sessao.execute(
        select(Document)
        .where(Document.company_id == company_id)
        .where(Document.name == nome_arquivo)
    )
    documentos_antigos = resultado.scalars().all()

    for documento in documentos_antigos:
        await sessao.delete(documento)

    if documentos_antigos:
        await sessao.flush()

    return len(documentos_antigos)


async def processar_arquivo(
    caminho: Path,
    company_id: UUID,
    agent_id: UUID,
) -> bool:
    """
    Processa um arquivo, substituindo qualquer versão anterior.

    Args:
        caminho: caminho completo do arquivo
        company_id: UUID da empresa dona do documento
        agent_id: UUID do agente associado

    Returns:
        True se processou com sucesso, False se falhou
    """
    print(f"\n📄 Processando: {caminho.name}")

    async with AsyncSessionLocal() as sessao:
        # Sempre apaga a versão anterior (se existir) antes de recriar —
        # garante que nunca fica conteúdo duplicado ou desatualizado.
        apagados = await apagar_versao_anterior(sessao, company_id, caminho.name)
        if apagados:
            print(
                f"  🗑️  Versão anterior encontrada e apagada "
                f"({apagados} documento(s), chunks removidos em cascata)"
            )

        # ── 1. Extrai o texto do arquivo ──────────────────────────────────
        texto = extrair_texto(caminho)
        if not texto or not texto.strip():
            print(f"  ❌ Texto vazio ou não extraído.")
            return False

        print(f"  📝 {len(texto)} caracteres extraídos")

        # ── 2. Divide o texto em chunks ───────────────────────────────────
        e_markdown = caminho.suffix.lower() == ".md"
        chunks = dividir_em_chunks(texto, e_markdown=e_markdown)
        print(
            f"  🔪 {len(chunks)} chunk(s) gerado(s)"
            f"{' (por seção, Markdown)' if e_markdown else ''}"
        )

        # ── 3. Cria o registro na tabela documents ────────────────────────
        # Fazemos isso antes dos chunks para ter o document_id disponível.
        # Se algo falhar depois, o commit não acontece e nada é salvo —
        # inclusive a exclusão da versão anterior é desfeita junto (mesma
        # transação), então nunca fica sem nenhuma versão no meio do caminho.
        from app.db.models.chunk import Chunk

        documento = Document(
            company_id=company_id,
            agent_id=agent_id,
            name=caminho.name,
            file_path=str(caminho),
            status="active",
        )
        sessao.add(documento)
        await sessao.flush()

        print(f"  🗂️  Documento registrado: {documento.id}")

        # ── 4. Gera embeddings e insere os chunks ─────────────────────────
        for i, conteudo_chunk in enumerate(chunks, start=1):
            embedding = await gerar_embedding(conteudo_chunk)

            chunk = Chunk(
                document_id=documento.id,
                company_id=company_id,
                agent_id=agent_id,
                content=conteudo_chunk,
                embedding=embedding,
            )
            sessao.add(chunk)
            print(f"  ✅ Chunk {i}/{len(chunks)} processado")

        # ── 5. Commit único — tudo ou nada ───────────────────────────────
        await sessao.commit()

    print(f"  ✅ Concluído: {caminho.name} ({len(chunks)} chunks salvos)\n")
    return True


async def main():
    parser = argparse.ArgumentParser(
        description="Ingere documentos no Knowledge Base do chatbot "
                     "(substitui automaticamente versões anteriores)"
    )
    parser.add_argument(
        "--company-id",
        required=True,
        help="UUID da empresa dona dos documentos",
    )
    parser.add_argument(
        "--agent-id",
        required=True,
        help="UUID do agente associado aos documentos",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Caminho de um arquivo específico (opcional). "
             "Se omitido, processa todos os arquivos da pasta da empresa.",
    )
    parser.add_argument(
        "--pasta",
        default=None,
        help="Nome da pasta da empresa dentro de knowledge_base/documents/ "
             "(padrão: 'default')",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Obsoleto — o script já substitui a versão anterior "
             "automaticamente. Mantido só para não quebrar comandos antigos.",
    )
    args = parser.parse_args()

    if args.forcar:
        print(
            "ℹ️  --forcar não é mais necessário: este script sempre "
            "substitui versões anteriores automaticamente.\n"
        )

    try:
        company_id = UUID(args.company_id)
        agent_id = UUID(args.agent_id)
    except ValueError as e:
        print(f"❌ UUID inválido: {e}")
        return

    # ── Modo arquivo único ────────────────────────────────────────────────
    if args.file:
        caminho = Path(args.file)
        if not caminho.exists():
            print(f"❌ Arquivo não encontrado: {caminho}")
            return
        await processar_arquivo(caminho, company_id, agent_id)
        return

    # ── Modo pasta (todos os arquivos da empresa) ─────────────────────────
    nome_pasta = args.pasta or "default"
    pasta = PASTA_KNOWLEDGE_BASE / nome_pasta

    if not pasta.exists():
        print(f"❌ Pasta não encontrada: {pasta}")
        print(f"   Crie a pasta e adicione os documentos antes de rodar o script.")
        print(f"   mkdir -p {pasta}")
        return

    arquivos = [a for a in pasta.glob("*") if a.is_file()]

    if not arquivos:
        print(f"⚠️  Nenhum arquivo encontrado em: {pasta}")
        return

    print(f"\n🚀 Iniciando ingestão")
    print(f"   Empresa:  {company_id}")
    print(f"   Agente:   {agent_id}")
    print(f"   Pasta:    {pasta}")
    print(f"   Arquivos: {len(arquivos)} encontrado(s)")
    print(f"   Modo:     substituição automática (sempre atualiza)")
    print("─" * 50)

    processados = 0
    erros = 0

    for arquivo in sorted(arquivos):
        try:
            sucesso = await processar_arquivo(arquivo, company_id, agent_id)
            if sucesso:
                processados += 1
            else:
                erros += 1
        except Exception as e:
            print(f"  ❌ Erro ao processar {arquivo.name}: {e}")
            erros += 1

    print("─" * 50)
    print(f"\n📊 Resumo:")
    print(f"   ✅ Processados: {processados}")
    print(f"   ❌ Erros:       {erros}")


if __name__ == "__main__":
    asyncio.run(main())
