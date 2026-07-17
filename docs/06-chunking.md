# 6. Chunking

## 6.1 O que é um chunk, e por que ele existe

Um **chunk** é um pedaço menor de um texto maior. Em vez de tratar um
documento inteiro (que pode ter várias páginas) como um único bloco, o
sistema o corta em pedaços de tamanho controlado antes de processá-lo.

Por que isso é necessário: modelos de IA e de embedding têm um limite de
quanto texto conseguem processar de uma vez, e mesmo dentro do limite,
textos muito longos "diluem" a relevância — se você manda um documento
inteiro de 10 páginas como contexto para uma pergunta específica sobre um
único parágrafo, o modelo tem mais dificuldade de focar no que importa
(além de custar mais, já que a cobrança da OpenAI é por quantidade de texto
processado). Cortando em pedaços menores, a busca semântica (capítulo 7)
consegue achar exatamente o parágrafo relevante, sem carregar o documento
inteiro a cada pergunta.

## 6.2 Implementação real (`chunking_service.py`)

```python
def dividir_em_chunks(texto: str, tamanho: int = 800, sobreposicao: int = 150) -> list[str]:
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
```

O algoritmo é simples e direto: corta o texto em janelas de **800
caracteres**, avançando **650 caracteres** por vez (800 − 150 de
sobreposição). Não é "inteligente" no sentido de respeitar frases ou
parágrafos — é um corte por posição de caractere.

## 6.3 Por que existe sobreposição (overlap)

Se o corte fosse seco, sem sobreposição, uma informação que estivesse
exatamente na fronteira entre dois chunks (ex: o fim de uma frase que
continua no início do próximo pedaço) ficaria partida ao meio em ambos os
chunks, e a busca vetorial poderia não reconhecer nenhum dos dois como
suficientemente relevante. Com 150 caracteres de sobreposição, o final de um
chunk sempre reaparece no início do próximo — garantindo que nenhuma frase
fique cortada sem contexto nos dois lados.

## 6.4 Exemplo real

Texto de entrada (documento de teste usado durante o desenvolvimento):

```
Informações sobre o Plano Especial DataFy-Y77:
Este é um plano experimental usado exclusivamente para testes de isolamento entre empresas.
A taxa de adesão deste plano é de exatamente R$ 9.999,00.
O prazo de ativação é de 12 dias úteis.
O código de referência interno deste plano é QW-3301.
```

Como esse texto tem menos de 800 caracteres, ele vira um **único chunk** —
o loop roda uma vez só (`inicio=0`, `fim=800`, mas o texto acaba antes
disso), gera um chunk com o texto inteiro, e para (porque `inicio` já passa
do tamanho do texto na próxima iteração). Documentos maiores que 800
caracteres gerariam múltiplos chunks, cada um com até 800 caracteres e 150
de sobreposição com o vizinho.

## 6.5 Vantagens e desvantagens desse tamanho

| | Chunks menores (ex: 300) | Chunks maiores (ex: 2000) |
|---|---|---|
| **Precisão da busca** | Mais precisa — cada chunk é sobre uma coisa só | Menos precisa — chunk pode misturar assuntos |
| **Contexto para a IA** | Pode faltar contexto ao redor da informação | Mais contexto, resposta mais completa |
| **Custo de embedding** | Mais chunks = mais chamadas à API de embedding | Menos chunks = menos chamadas |
| **Risco de "cortar no meio"** | Maior (mais cortes) | Menor (menos cortes) |

800/150 é um valor intermediário, adequado para documentos de texto corrido
como os deste projeto (informações de produtos, taxas, prazos). Se no futuro a
qualidade das respostas parecer estar perdendo contexto (respostas
incompletas), aumentar o `tamanho` é o primeiro ajuste a testar. Se a busca
estiver trazendo chunks "misturados" com informação irrelevante junto da
relevante, diminuir o `tamanho` é o ajuste indicado.

## 6.6 Impacto de mudar esses valores

Importante: mudar `tamanho`/`sobreposicao` no código **não afeta chunks já
existentes no banco** — só os próximos documentos ingeridos. Para aplicar um
novo valor a documentos antigos, é necessário apagar os chunks existentes
(ver [capítulo 5.6](./05-base-de-conhecimento.md)) e rodar a ingestão de
novo com `--forcar`.
