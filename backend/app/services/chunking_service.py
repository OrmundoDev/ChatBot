import re


def dividir_em_chunks(
    texto: str,
    tamanho: int = 800,
    sobreposicao: int = 150,
    e_markdown: bool = False,
) -> list[str]:
    """
    Divide um texto longo em pedaços (chunks) de tamanho aproximado,
    com sobreposição entre eles para não perder contexto nas bordas.

    Se e_markdown=True, tenta primeiro dividir por seção (títulos
    ## ou ###), mantendo cada seção como um chunk único sempre que
    couber dentro do limite de tamanho — isso evita cortar tabelas
    e parágrafos no meio. Seções grandes demais caem no método
    antigo (corte por caractere), mas mantendo o título da seção
    como contexto em cada pedaço gerado.

    Quando e_markdown=False (padrão), o comportamento é idêntico ao
    método original — usado por arquivos .txt e .pdf, sem nenhuma
    mudança de resultado.
    """
    texto = texto.strip()

    if e_markdown:
        return _dividir_markdown_por_secao(texto, tamanho, sobreposicao)

    chunks = []
    inicio = 0

    while inicio < len(texto):
        fim = inicio + tamanho
        pedaco = texto[inicio:fim].strip()
        if pedaco:
            chunks.append(pedaco)
        inicio += tamanho - sobreposicao

    return chunks


def _dividir_markdown_por_secao(
    texto: str,
    tamanho: int,
    sobreposicao: int,
) -> list[str]:
    """
    Divide um texto Markdown por seção (## ou ###), mantendo o título
    de cada seção junto do seu conteúdo em um único chunk sempre que
    possível.
    """
    # Seções podem ser um pouco maiores que o tamanho padrão (folga de
    # 50%) antes de precisarem ser sub-divididas — tabelas e listas
    # costumam deixar uma seção um pouco mais longa sem perder coesão.
    limite_secao = int(tamanho * 1.5)

    # re.split com grupo capturado mantém os títulos na lista resultante:
    # [preambulo, titulo1, conteudo1, titulo2, conteudo2, ...]
    partes = re.split(r'(?m)^(#{2,3} .+)$', texto)

    secoes = []

    preambulo = partes[0].strip()
    if preambulo:
        secoes.append(preambulo)

    for i in range(1, len(partes), 2):
        titulo = partes[i].strip()
        conteudo = partes[i + 1].strip() if i + 1 < len(partes) else ""
        secao_completa = f"{titulo}\n\n{conteudo}".strip()
        if secao_completa:
            secoes.append(secao_completa)

    chunks = []
    for secao in secoes:
        if len(secao) <= limite_secao:
            chunks.append(secao)
            continue

        # Seção grande demais: cai no corte por caractere, mas repete
        # o título em cada pedaço para não perder o contexto de qual
        # assunto aquele pedaço pertence.
        linhas = secao.split("\n", 1)
        titulo = linhas[0] if len(linhas) > 1 else ""
        corpo = linhas[1] if len(linhas) > 1 else secao

        inicio = 0
        while inicio < len(corpo):
            fim = inicio + tamanho
            pedaco = corpo[inicio:fim].strip()
            if pedaco:
                prefixo = f"{titulo}\n\n" if titulo else ""
                chunks.append(f"{prefixo}{pedaco}")
            inicio += tamanho - sobreposicao

    return chunks
