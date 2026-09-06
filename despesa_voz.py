"""Transcrição e interpretação de despesas ditadas em português."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, Field


CATEGORIAS_FIXAS = (
    "Alimentação",
    "Lazer",
    "Higiene",
    "Saúde",
    "Transporte",
    "Casa",
    "Outros",
)

CATEGORIAS_POR_PALAVRA = {
    "Alimentação": (
        "almoco", "jantar", "lanche", "cafe", "restaurante", "mercado",
        "padaria", "pizza", "ifood", "comida", "whey", "suplemento",
    ),
    "Lazer": (
        "cinema", "show", "viagem", "passeio", "bar", "ingresso", "jogo",
        "game", "videogame", "playstation", "xbox", "steam",
    ),
    "Higiene": (
        "sabonete", "shampoo", "condicionador", "desodorante", "creme dental",
        "pasta de dente", "escova de dente", "higiene",
    ),
    "Saúde": ("farmacia", "remedio", "medico", "consulta", "dentista", "exame"),
    "Transporte": (
        "uber", "99", "taxi", "gasolina", "combustivel", "estacionamento",
        "onibus", "metro", "pedagio", "passagem",
    ),
    "Casa": (
        "aluguel", "condominio", "energia", "luz", "agua", "internet",
        "gas", "moveis", "eletrodomestico", "manutencao", "reparo",
    ),
}

NUMEROS_EXTENSOS = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3,
    "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14,
    "quatorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17,
    "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30,
    "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70,
    "oitenta": 80, "noventa": 90, "cem": 100, "cento": 100,
    "duzentos": 200, "trezentos": 300, "quatrocentos": 400,
    "quinhentos": 500, "seiscentos": 600, "setecentos": 700,
    "oitocentos": 800, "novecentos": 900,
}


class DespesaInterpretada(BaseModel):
    descricao: str = Field(
        min_length=1,
        max_length=60,
        description="Resumo curto da compra, sem preço ou parcelas",
    )
    valor: float | None = Field(description="Valor total em reais")
    categoria: Literal[
        "Alimentação", "Lazer", "Higiene", "Saúde", "Transporte", "Casa", "Outros"
    ]
    parcelas: int = Field(ge=1, le=120)
    responsavel: Literal["Rafael", "Nathalia"] | None


def normalizar_texto(texto: str) -> str:
    sem_acentos = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acentos if not unicodedata.combining(c)).lower()


def _converter_valor(valor: str) -> float:
    limpo = re.sub(r"[^\d,.]", "", valor)
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif limpo.count(".") == 1 and len(limpo.rsplit(".", 1)[1]) == 3:
        limpo = limpo.replace(".", "")
    return float(limpo)


def _converter_numero_extenso(texto: str) -> float | None:
    total = 0
    atual = 0
    encontrou_numero = False
    for palavra in normalizar_texto(texto).split():
        if palavra == "e":
            continue
        if palavra == "mil":
            total += max(atual, 1) * 1000
            atual = 0
            encontrou_numero = True
        elif palavra in NUMEROS_EXTENSOS:
            atual += NUMEROS_EXTENSOS[palavra]
            encontrou_numero = True
        else:
            return None
    return float(total + atual) if encontrou_numero else None


def _encontrar_valor_extenso(texto: str) -> tuple[float | None, tuple[int, int] | None]:
    texto_normalizado = normalizar_texto(texto)
    numeros = sorted(NUMEROS_EXTENSOS, key=len, reverse=True)
    inicio = "|".join(re.escape(numero) for numero in numeros)
    continuacao = f"{inicio}|mil|e"
    padrao = rf"\b((?:{inicio})(?:\s+(?:{continuacao}))*)\s+reais?\b"
    encontrados = list(re.finditer(padrao, texto_normalizado))
    if not encontrados:
        return None, None
    encontrado = encontrados[-1]
    return _converter_numero_extenso(encontrado.group(1)), encontrado.span()


def _encontrar_valor(texto: str) -> tuple[float | None, tuple[int, int] | None]:
    numero = r"(?:\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)(?!\d)"
    padroes = (
        rf"(?:por|custou|deu|paguei|valor(?:\s+de)?)\s+(?:r\$\s*)?({numero})",
        rf"r\$\s*({numero})",
        rf"({numero})\s*(?:reais|real)\b",
    )
    for padrao in padroes:
        encontrado = re.search(padrao, texto, flags=re.IGNORECASE)
        if encontrado:
            return _converter_valor(encontrado.group(1)), encontrado.span()

    valor_extenso, intervalo_extenso = _encontrar_valor_extenso(texto)
    if valor_extenso is not None:
        return valor_extenso, intervalo_extenso

    numeros = list(re.finditer(numero, texto))
    if numeros:
        encontrado = numeros[-1]
        return _converter_valor(encontrado.group()), encontrado.span()
    return None, None


def _inferir_categoria(texto_normalizado: str) -> str:
    for categoria, palavras in CATEGORIAS_POR_PALAVRA.items():
        if any(re.search(rf"\b{re.escape(palavra)}\b", texto_normalizado) for palavra in palavras):
            return categoria
    return "Outros"


def _extrair_descricao(texto: str, intervalo_valor: tuple[int, int] | None) -> str:
    antes = texto[: intervalo_valor[0]] if intervalo_valor else texto
    depois = texto[intervalo_valor[1] :] if intervalo_valor else ""
    antes = re.sub(
        r"^\s*(?:eu\s+)?(?:comprei|gastei|paguei|parcelei|foi|adicione|adicionar|lance|lancar)\s+",
        "", antes, flags=re.IGNORECASE,
    )
    antes = re.sub(r"\b(?:parcelado\s+)?em\s+(?:\d+|\w+)\s+(?:x|vezes|parcelas)\b", "", antes, flags=re.IGNORECASE)
    antes = re.sub(r"\s+(?:por|de|deu|custou|valor(?:\s+de)?)\s*$", "", antes, flags=re.IGNORECASE)
    antes = re.sub(r"^\s*(?:um|uma|o|a)\s+", "", antes, flags=re.IGNORECASE)
    descricao = antes.strip(" ,.-")
    if not descricao:
        depois = re.sub(r"^\s*(?:reais|real)?\s*", "", depois, flags=re.IGNORECASE)
        depois = re.sub(
            r"\b(?:com|no|na|pelo|pela)\s+(?:cart[aã]o(?:\s+de\s+cr[eé]dito)?|cr[eé]dito|vr|ticket)\b.*$",
            "", depois, flags=re.IGNORECASE,
        )
        depois = re.sub(r"\b(?:em\s+)?\d+\s*(?:x|vezes|parcelas)\b.*$", "", depois, flags=re.IGNORECASE)
        depois = re.sub(r"^\s*(?:em|no|na)\s+(?:uma|um)?\s*", "", depois, flags=re.IGNORECASE)
        descricao = depois.strip(" ,.-")
    if re.search(r"\bwhey\b", normalizar_texto(texto)):
        return "Whey para dieta"
    return descricao.capitalize()


def interpretar_despesa(texto: str) -> dict[str, Any]:
    """Converte uma frase curta em valores iniciais para o formulário."""
    texto = texto.strip()
    normalizado = normalizar_texto(texto)
    valor, intervalo = _encontrar_valor(texto)

    match_parcelas = re.search(r"(?:em\s+)?(\d+)\s*(?:x|vezes|parcelas)\b", normalizado)
    parcelas = max(1, int(match_parcelas.group(1))) if match_parcelas else 1
    if not match_parcelas:
        palavras_parcelas = re.search(r"(?:em\s+)?([a-z]+)\s+(?:vezes|parcelas)\b", normalizado)
        if palavras_parcelas:
            numero_parcelas = _converter_numero_extenso(palavras_parcelas.group(1))
            if numero_parcelas:
                parcelas = max(1, int(numero_parcelas))

    responsavel = None
    if re.search(r"\brafael\b", normalizado):
        responsavel = "Rafael"
    elif re.search(r"\bnathalia\b", normalizado):
        responsavel = "Nathalia"

    return {
        "transcricao": texto,
        "descricao": _extrair_descricao(texto, intervalo),
        "valor": valor,
        "categoria": _inferir_categoria(normalizado),
        "parcelas": parcelas,
        "responsavel": responsavel,
    }


def interpretar_despesa_com_ia(texto: str, api_key: str) -> dict[str, Any]:
    """Extrai os campos semanticamente com saída validada pelo schema."""
    from openai import OpenAI

    cliente = OpenAI(api_key=api_key)
    resposta = cliente.responses.parse(
        model="gpt-4o-mini",
        instructions=(
            "Extraia uma única despesa ditada em português do Brasil. "
            "Converta números por extenso em números. O valor deve ser o total da compra. "
            "Use parcelas=1 quando o parcelamento não for mencionado. "
            "A descrição deve ter de 1 a 5 palavras, sem preço, moeda, parcelas, data "
            "ou responsável. Resuma o item e seu contexto útil; por exemplo, 'whey na "
            "academia' vira 'Whey para dieta' e 'lanche de trinta reais' vira 'Lanche'. "
            "Classifique jogos, videogame, cinema e passeios como Lazer; refeições, "
            "mercado, whey e suplementos como Alimentação; produtos de cuidado pessoal "
            "como Higiene; remédios, consultas e exames como Saúde; combustível, Uber, "
            "táxi, transporte público, estacionamento e pedágio como Transporte; aluguel, "
            "condomínio, contas domésticas, móveis e reparos residenciais como Casa. Use Outros somente "
            "quando nenhuma categoria se aplicar. Só defina o responsável se o nome for dito."
        ),
        input=texto,
        text_format=DespesaInterpretada,
        store=False,
    )
    if resposta.output_parsed is None:
        raise ValueError("A resposta não continha uma despesa estruturada.")
    return resposta.output_parsed.model_dump()


def transcrever_audio(audio: Any, api_key: str) -> str:
    """Envia o WAV gravado pelo Streamlit para a API de transcrição."""
    from openai import OpenAI

    cliente = OpenAI(api_key=api_key)
    resposta = cliente.audio.transcriptions.create(
        model="gpt-transcribe",
        file=(
            getattr(audio, "name", "despesa.wav"),
            audio.getvalue(),
            getattr(audio, "type", "audio/wav"),
        ),
        prompt=(
            "Despesa pessoal em português do Brasil. Escreva valores monetários com "
            "algarismos (por exemplo: trinta reais deve virar 30 reais). Preserve nomes "
            "de produtos, estabelecimentos, Rafael e Nathalia."
        ),
    )
    return resposta.text.strip()
