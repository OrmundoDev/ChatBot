import asyncio
from app.services.ollama_service import perguntar_para_ia

async def testar():
    # Pergunta dentro do KB
    r1 = await perguntar_para_ia(
        pergunta="O que é exigido para o visto de trabalho temporário?",
        contexto="O visto de trabalho temporário H exige carta da empresa contratante."
    )
    print("DENTRO DO KB ->", r1)

    # Pergunta fora do KB, mas com contexto irrelevante presente
    r2 = await perguntar_para_ia(
        pergunta="Qual a capital da França?",
        contexto="O visto de trabalho temporário H exige carta da empresa contratante."
    )
    print("FORA DO KB ->", r2)

asyncio.run(testar())
