def dividir_em_chunks(texto: str, tamanho: int = 800, sobreposicao: int = 150) -> list[str]:
    """
    Divide um texto longo em pedaços (chunks) de tamanho aproximado,
    com sobreposição entre eles para não perder contexto nas bordas.
    """
    texto = texto.strip()
    chunks = []
    inicio = 0

    while inicio < len(texto):
        fim = inicio + tamanho
        pedaco = texto[inicio:fim].strip()
        if pedaco:
            chunks.append(pedaco)
        inicio += tamanho - sobreposicao

    return chunks
