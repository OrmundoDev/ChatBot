from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    pergunta: str = Field(
        ...,
        min_length=1,
        description="Pergunta enviada pelo usuario"
    )


class ChatResponse(BaseModel):
    resposta: str
