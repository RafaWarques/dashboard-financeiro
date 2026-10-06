"""Persistência da lista de desejos e das fotos, sem dependência da interface."""
from __future__ import annotations

import warnings
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from uuid import UUID, uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

BUCKET = "wishlist-fotos"
LIMITE_FOTO = 5 * 1024 * 1024
RESPONSAVEIS = ("Rafael", "Nathalia")


class ErroWishlist(Exception):
    """Erro seguro para apresentação na interface."""


def validar_item(nome, valor, descricao, responsavel):
    nome = str(nome).strip()
    descricao = str(descricao or "").strip()
    if not 1 <= len(nome) <= 120:
        raise ErroWishlist("Informe um nome com até 120 caracteres.")
    if len(descricao) > 2000:
        raise ErroWishlist("A descrição deve ter até 2.000 caracteres.")
    if responsavel not in RESPONSAVEIS:
        raise ErroWishlist("Selecione um responsável válido.")
    try:
        quantia = Decimal(str(valor))
        if not quantia.is_finite() or not 0 < quantia <= Decimal("9999999999.99"):
            raise InvalidOperation
        quantia = quantia.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if quantia <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        raise ErroWishlist("Informe um valor maior que zero, com no máximo 10 dígitos inteiros.") from None
    return {"nome": nome, "valor": str(quantia), "descricao": descricao, "responsavel": responsavel}


def preparar_foto(conteudo: bytes) -> bytes:
    if not conteudo or len(conteudo) > LIMITE_FOTO:
        raise ErroWishlist("A foto deve ter até 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(conteudo)) as original:
                if original.format not in ("JPEG", "PNG", "WEBP"):
                    raise ErroWishlist("Use uma foto JPG, PNG ou WebP.")
                # Limita o custo de decodificação, além do limite de bytes.
                if original.width * original.height > 25_000_000:
                    raise ErroWishlist("A foto deve ter no máximo 25 megapixels.")
                imagem = ImageOps.exif_transpose(original)
                imagem.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                rgba = imagem.convert("RGBA")
                fundo = Image.new("RGB", rgba.size, "white")
                fundo.paste(rgba, mask=rgba.getchannel("A"))
                saida = BytesIO()
                # Não repassa EXIF, incluindo coordenadas GPS, ao arquivo final.
                fundo.save(saida, format="JPEG", quality=85, optimize=True)
                return saida.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ErroWishlist("Não consegui abrir a foto. Escolha outra imagem JPG, PNG ou WebP.") from None


class WishlistRepositorio:
    def __init__(self, cliente):
        self.cliente = cliente

    @property
    def fotos(self):
        return self.cliente.storage.from_(BUCKET)

    def listar(self):
        try:
            # Paginação evita o limite padrão de 1.000 registros do Supabase.
            itens, inicio = [], 0
            while True:
                pagina = (self.cliente.table("wishlist_itens").select("*")
                          .order("criado_em", desc=True).order("id")
                          .range(inicio, inicio + 499).execute().data)
                itens.extend(pagina)
                if len(pagina) < 500:
                    return itens
                inicio += 500
        except Exception as erro:
            raise ErroWishlist(
                "Não consegui carregar a lista. Confira a conexão, a chave de servidor e a "
                "migração supabase/migrations/20261006120000_wishlist.sql."
            ) from erro

    def _apagar_foto(self, caminho):
        if not caminho:
            return None
        try:
            self.fotos.remove([caminho])
        except Exception:
            return ("O item foi atualizado, mas uma foto antiga ficou no Storage. "
                    f"Remova o arquivo {caminho} do bucket {BUCKET}.")
        return None

    def salvar(self, nome, valor, descricao, responsavel, *, item=None, foto=None, remover_foto=False):
        dados = validar_item(nome, valor, descricao, responsavel)
        identificador = str(UUID(str(item["id"]))) if item else str(uuid4())
        antiga = item.get("foto_path") if item else None
        nova = None
        if foto is not None:
            conteudo = preparar_foto(foto)
            nova = f"{identificador}/{uuid4().hex}.jpg"
            try:
                self.fotos.upload(nova, conteudo, file_options={
                    "content-type": "image/jpeg", "upsert": "false", "cache-control": "3600",
                })
            except Exception as erro:
                raise ErroWishlist("Não consegui enviar a foto. Confira o bucket wishlist-fotos e tente novamente.") from erro
        dados["foto_path"] = nova or (None if remover_foto else antiga)
        try:
            tabela = self.cliente.table("wishlist_itens")
            resposta = (tabela.update(dados).eq("id", identificador) if item
                        else tabela.insert({"id": identificador, **dados})).execute()
            if not resposta.data:
                raise ErroWishlist("Este item não existe mais. Atualize a lista.")
        except Exception as erro:
            aviso = self._apagar_foto(nova)
            mensagem = "Não consegui salvar o item. Seus campos foram mantidos para tentar novamente."
            if aviso:
                mensagem += f" Há uma foto sem item: {nova}. Remova-a do bucket {BUCKET}."
            raise ErroWishlist(mensagem) from erro
        aviso = self._apagar_foto(antiga) if antiga and antiga != dados["foto_path"] else None
        return aviso

    def mudar_status(self, item):
        comprado = item["status"] != "comprado"
        dados = {"status": "comprado" if comprado else "desejado",
                 "comprado_em": datetime.now(timezone.utc).isoformat() if comprado else None}
        try:
            resposta = self.cliente.table("wishlist_itens").update(dados).eq("id", item["id"]).execute()
            if not resposta.data:
                raise ErroWishlist("Este item não existe mais. Atualize a lista.")
        except Exception as erro:
            raise ErroWishlist("Não consegui alterar o status. Atualize a lista e tente novamente.") from erro

    def excluir(self, item):
        try:
            self.cliente.table("wishlist_itens").delete().eq("id", item["id"]).execute()
        except Exception as erro:
            raise ErroWishlist("Não consegui excluir o item. Tente novamente.") from erro
        return self._apagar_foto(item.get("foto_path"))

    def url_foto(self, caminho):
        try:
            # O banco armazena somente o caminho. A URL expira em uma hora.
            resposta = self.fotos.create_signed_url(caminho, 3600)
            return resposta["signedURL"]
        except Exception as erro:
            raise ErroWishlist("Foto indisponível no momento. Você pode continuar usando o item.") from erro
