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

Como funciona:
1. Busca os arquivos da pasta da empresa (ou o arquivo especificado)
2. Para cada arquivo:
   a. Cria um registro na tabela 'documents'
   b. Extrai o texto (PDF ou TXT)
   c. Divide em chunks com sobreposição
   d. Gera embedding para cada chunk
   e. Salva na tabela 'chunks' com company_id e agent_id
3. O KnowledgeService já filtra por company_id nas buscas RAG
"""

import asyncio
import argparse
from pathlib import Path
from uuid import UUID

from pypdf import PdfReader
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models.document import Document
from app.db.models.chunk import Chunk
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
    else:
        print(f"  ⚠️  Formato não suportado, ignorando: {caminho.name}")
        return None


async def documento_ja_processado(
    sessao,
    company_id: UUID,
    nome_arquivo: str,
) -> bool:
    """
    Verifica se o arquivo já foi processado para esta empresa.

    Evita duplicar chunks se o script for executado duas vezes
    com o mesmo arquivo.
    """
    resultado = await sessao.execute(
        select(Document)
        .where(Document.company_id == company_id)
        .where(Document.name == nome_arquivo)
        .where(Document.status == "active")
    )
    return resultado.scalar_one_or_none() is not None


async def processar_arquivo(
    caminho: Path,
    company_id: UUID,
    agent_id: UUID,
    forcar: bool = False,
) -> bool:
    """
    Processa um arquivo e insere seus chunks no banco.

    Args:
        caminho: caminho completo do arquivo
        company_id: UUID da empresa dona do documento
        agent_id: UUID do agente associado
        forcar: se True, reprocessa mesmo se já existir

    Returns:
        True se processou com sucesso, False se pulou ou falhou
    """
    print(f"\n📄 Processando: {caminho.name}")

    async with AsyncSessionLocal() as sessao:
        # Verifica duplicidade antes de processar
        if not forcar and await documento_ja_processado(sessao, company_id, caminho.name):
            print(f"  ⏭️  Já processado anteriormente. Use --forcar para reprocessar.")
            return False

        # ── 1. Extrai o texto do arquivo ──────────────────────────────────
        texto = extrair_texto(caminho)
        if not texto or not texto.strip():
            print(f"  ❌ Texto vazio ou não extraído.")
            return False

        print(f"  📝 {len(texto)} caracteres extraídos")

        # ── 2. Divide o texto em chunks ───────────────────────────────────
        chunks = dividir_em_chunks(texto)
        print(f"  🔪 {len(chunks)} chunk(s) gerado(s)")

        # ── 3. Cria o registro na tabela documents ────────────────────────
        # Fazemos isso antes dos chunks para ter o document_id disponível.
        # Se algo falhar depois, o commit não acontece e nada é salvo.
        documento = Document(
            company_id=company_id,
            agent_id=agent_id,
            name=caminho.name,
            file_path=str(caminho),
            status="active",
        )
        sessao.add(documento)
        # flush() gera o UUID do documento sem commitar ainda
        await sessao.flush()

        print(f"  🗂️  Documento registrado: {documento.id}")

        # ── 4. Gera embeddings e insere os chunks ─────────────────────────
        for i, conteudo_chunk in enumerate(chunks, start=1):
            embedding = await gerar_embedding(conteudo_chunk)

            chunk = Chunk(
                document_id=documento.id,   # FK para o documento pai
                company_id=company_id,       # duplicado para otimizar busca RAG
                agent_id=agent_id,
                content=conteudo_chunk,
                embedding=embedding,
            )
            sessao.add(chunk)
            print(f"  ✅ Chunk {i}/{len(chunks)} processado")

        # ── 5. Commit único — tudo ou nada ───────────────────────────────
        # Se qualquer chunk falhar, o documento também não é salvo.
        # Isso garante consistência: nunca haverá documento sem chunks.
        await sessao.commit()

    print(f"  ✅ Concluído: {caminho.name} ({len(chunks)} chunks salvos)\n")
    return True


async def main():
    parser = argparse.ArgumentParser(
        description="Ingere documentos no Knowledge Base do chatbot"
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
             "(padrão: usa o slug da empresa ou 'default')",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Reprocessa arquivos mesmo se já foram processados antes",
    )
    args = parser.parse_args()

    # Valida e converte os UUIDs
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
        await processar_arquivo(caminho, company_id, agent_id, args.forcar)
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
    print(f"   Forçar:   {'sim' if args.forcar else 'não (pula duplicados)'}")
    print("─" * 50)

    processados = 0
    pulados = 0
    erros = 0

    for arquivo in sorted(arquivos):
        try:
            sucesso = await processar_arquivo(
                arquivo, company_id, agent_id, args.forcar
            )
            if sucesso:
                processados += 1
            else:
                pulados += 1
        except Exception as e:
            print(f"  ❌ Erro ao processar {arquivo.name}: {e}")
            erros += 1

    print("─" * 50)
    print(f"\n📊 Resumo:")
    print(f"   ✅ Processados: {processados}")
    print(f"   ⏭️  Pulados:     {pulados}")
    print(f"   ❌ Erros:       {erros}")


if __name__ == "__main__":
    asyncio.run(main())