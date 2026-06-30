import asyncio
from pathlib import Path

from pypdf import PdfReader

from app.db.session import AsyncSessionLocal
from app.db.models import DocumentoChunk
from app.services.embedding_service import gerar_embedding
from app.services.chunking_service import dividir_em_chunks

PASTA_DOCUMENTOS = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "documents"


def extrair_texto_pdf(caminho: Path) -> str:
    leitor = PdfReader(str(caminho))
    paginas = [pagina.extract_text() or "" for pagina in leitor.pages]
    return "\n".join(paginas)


async def processar_arquivo(caminho: Path):
    print(f"Processando: {caminho.name}")

    if caminho.suffix.lower() == ".pdf":
        texto = extrair_texto_pdf(caminho)
    elif caminho.suffix.lower() == ".txt":
        texto = caminho.read_text(encoding="utf-8")
    else:
        print(f"  Formato não suportado, ignorando: {caminho.name}")
        return

    chunks = dividir_em_chunks(texto)
    print(f"  {len(chunks)} pedaço(s) gerado(s)")

    async with AsyncSessionLocal() as sessao:
        for i, chunk in enumerate(chunks, start=1):
            embedding = await gerar_embedding(chunk)
            novo_chunk = DocumentoChunk(
                nome_arquivo=caminho.name,
                conteudo=chunk,
                embedding=embedding
            )
            sessao.add(novo_chunk)
            print(f"  Chunk {i}/{len(chunks)} processado")
        await sessao.commit()

    print(f"Concluído: {caminho.name}\n")


async def main():
    if not PASTA_DOCUMENTOS.exists():
        print(f"Pasta não encontrada: {PASTA_DOCUMENTOS}")
        return

    arquivos = [a for a in PASTA_DOCUMENTOS.glob("*") if a.is_file()]
    if not arquivos:
        print("Nenhum documento encontrado em knowledge_base/documents/")
        return

    for arquivo in arquivos:
        await processar_arquivo(arquivo)


if __name__ == "__main__":
    asyncio.run(main())
