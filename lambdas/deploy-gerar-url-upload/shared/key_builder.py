"""
Módulo de construção de chaves (keys) S3 para o Cofre Digital.

Responsável por montar os caminhos completos dos objetos no bucket,
incluindo prefixos, categorias e nomes de arquivo.
"""

import os
import uuid
import urllib.parse


def build_upload_key(prefix, category, filename):
    """
    Constrói a chave S3 para upload de um documento no prefixo de entrada.

    Formato: {prefix}/{category}/{uuid}_{filename}

    Args:
        prefix: Prefixo base (ex: 'entrada')
        category: Subcategoria (ex: 'contratos', 'notas-fiscais')
        filename: Nome do arquivo sanitizado

    Returns:
        String com a chave completa do objeto no S3.
    """
    # Gera UUID para evitar colisões de nome
    unique_id = uuid.uuid4().hex[:8]
    safe_filename = f"{unique_id}_{filename}"
    return f"{prefix}/{category}/{safe_filename}"


def build_processed_key(source_key, processed_prefix):
    """
    Constrói a chave de destino no prefixo processados/ a partir da chave de origem.

    Mantém a subcategoria e o nome do arquivo.
    Ex: entrada/contratos/abc123_doc.pdf → processados/contratos/abc123_doc.pdf

    Args:
        source_key: Chave original do objeto (ex: 'entrada/contratos/arquivo.pdf')
        processed_prefix: Prefixo de destino (ex: 'processados')

    Returns:
        String com a chave de destino no prefixo processados.
    """
    parts = source_key.split("/")

    if len(parts) >= 3:
        # entrada/categoria/arquivo.pdf → processados/categoria/arquivo.pdf
        category = parts[1]
        filename = "/".join(parts[2:])
        return f"{processed_prefix}/{category}/{filename}"
    elif len(parts) == 2:
        # entrada/arquivo.pdf → processados/outros/arquivo.pdf
        filename = parts[1]
        return f"{processed_prefix}/outros/{filename}"
    else:
        # Caso inesperado: usa o nome original
        return f"{processed_prefix}/outros/{source_key}"


def build_rejected_key(source_key, rejected_prefix):
    """
    Constrói a chave de destino no prefixo rejeitados/ a partir da chave de origem.

    Arquivos rejeitados vão para a raiz do prefixo rejeitados/.
    Ex: entrada/contratos/arquivo.exe → rejeitados/arquivo.exe

    Args:
        source_key: Chave original do objeto
        rejected_prefix: Prefixo de destino (ex: 'rejeitados')

    Returns:
        String com a chave de destino no prefixo rejeitados.
    """
    filename = extract_filename(source_key)
    return f"{rejected_prefix}/{filename}"


def extract_filename(key):
    """
    Extrai o nome do arquivo a partir de uma chave S3 completa.

    Ex: 'processados/contratos/abc123_doc.pdf' → 'abc123_doc.pdf'

    Args:
        key: Chave completa do objeto S3.

    Returns:
        String com o nome do arquivo (último segmento da chave).
    """
    if not key:
        return ""
    # Decodifica caracteres especiais que podem vir codificados
    decoded_key = urllib.parse.unquote_plus(key)
    parts = decoded_key.split("/")
    return parts[-1] if parts else ""


def extract_category(key):
    """
    Extrai a subcategoria a partir de uma chave S3 completa.

    Ex: 'processados/contratos/abc123_doc.pdf' → 'contratos'
    Ex: 'entrada/notas-fiscais/nota.pdf' → 'notas-fiscais'

    Args:
        key: Chave completa do objeto S3.

    Returns:
        String com a subcategoria, ou 'outros' se não identificada.
    """
    if not key:
        return "outros"
    decoded_key = urllib.parse.unquote_plus(key)
    parts = decoded_key.split("/")
    # Formato esperado: prefixo/categoria/arquivo
    if len(parts) >= 3:
        return parts[1]
    return "outros"


def is_in_prefix(key, prefix):
    """
    Verifica se uma chave S3 está dentro de um determinado prefixo.

    Args:
        key: Chave do objeto S3.
        prefix: Prefixo a verificar (ex: 'entrada', 'processados')

    Returns:
        True se a chave começa com o prefixo seguido de '/'.
    """
    if not key or not prefix:
        return False
    # Garante que o prefixo termina com /
    normalized_prefix = prefix.rstrip("/") + "/"
    return key.startswith(normalized_prefix)


def decode_s3_key(key):
    """
    Decodifica uma chave S3 que pode conter caracteres codificados em URL.

    O S3 Event Notification codifica caracteres especiais como espaços (+)
    e outros caracteres não-ASCII.

    Args:
        key: Chave codificada do evento S3.

    Returns:
        String com a chave decodificada.
    """
    if not key:
        return ""
    return urllib.parse.unquote_plus(key)
