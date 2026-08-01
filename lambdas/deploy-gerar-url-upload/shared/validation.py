"""
Módulo de validação compartilhado para as funções Lambda do Cofre Digital.

Contém funções de validação de extensões, campos obrigatórios,
sanitização de nomes de arquivo e validação de categorias.
"""

import os
import re

# Extensões de arquivo permitidas para upload
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "csv", "xlsx", "txt"}

# Categorias válidas para organização de documentos
VALID_CATEGORIES = {"contratos", "notas-fiscais", "relatorios", "comprovantes", "outros"}

# Tamanho máximo de arquivo em megabytes
MAX_FILE_SIZE_MB = 20


def validate_extension(filename):
    """
    Valida se a extensão do arquivo está na lista de extensões permitidas.

    Args:
        filename: Nome do arquivo a ser validado.

    Returns:
        dict com 'valid' (bool) e 'error' (str) caso inválido.
        A mensagem de erro inclui a lista de extensões válidas.
    """
    if not filename or not isinstance(filename, str):
        return {
            "valid": False,
            "error": (
                "Nome do arquivo é obrigatório. "
                f"Extensões válidas: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        }

    # Extrai a extensão do arquivo (sem o ponto, em minúsculas)
    _, ext = os.path.splitext(filename)
    ext = ext.lstrip(".").lower()

    if not ext:
        return {
            "valid": False,
            "error": (
                "Extensão não permitida. "
                f"Extensões válidas: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        }

    if ext not in ALLOWED_EXTENSIONS:
        return {
            "valid": False,
            "error": (
                "Extensão não permitida. "
                f"Extensões válidas: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        }

    return {"valid": True}


def validate_required_fields(body, fields):
    """
    Verifica se todos os campos obrigatórios estão presentes e não-vazios no body.

    Args:
        body: Dicionário com os dados da requisição.
        fields: Lista de nomes dos campos obrigatórios.

    Returns:
        dict com 'valid' (bool) e 'missing_fields' (list) caso haja campos ausentes.
        A mensagem de erro indica os campos faltantes.
    """
    if not body or not isinstance(body, dict):
        return {
            "valid": False,
            "missing_fields": list(fields),
            "error": f"Campos obrigatórios ausentes: {', '.join(fields)}",
        }

    missing = []
    for field in fields:
        value = body.get(field)
        # Campo ausente ou vazio (string vazia, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)

    if missing:
        return {
            "valid": False,
            "missing_fields": missing,
            "error": f"Campos obrigatórios ausentes: {', '.join(missing)}",
        }

    return {"valid": True, "missing_fields": []}


def sanitize_filename(filename):
    """
    Sanitiza o nome do arquivo removendo sequências de travessia de caminho
    e caracteres perigosos.

    Remove:
        - Sequências de travessia: ../, ..\, ..
        - Separadores de caminho: / e \\
        - Caracteres de controle e caracteres perigosos

    Preserva:
        - O nome base do arquivo (com extensão)
        - Caracteres alfanuméricos, pontos, hífens, underscores e espaços

    Args:
        filename: Nome do arquivo a ser sanitizado.

    Returns:
        String com o nome do arquivo sanitizado.
    """
    if not filename or not isinstance(filename, str):
        return ""

    # Remove sequências de travessia de caminho
    sanitized = filename.replace("../", "")
    sanitized = sanitized.replace("..\\", "")
    sanitized = sanitized.replace("..", "")

    # Remove separadores de caminho restantes
    sanitized = sanitized.replace("/", "")
    sanitized = sanitized.replace("\\", "")

    # Remove caracteres de controle (ASCII 0-31)
    sanitized = re.sub(r"[\x00-\x1f]", "", sanitized)

    # Remove caracteres perigosos mas preserva acentos, espaços, hífens, underscores e pontos
    # Permite: letras (incluindo acentuadas), números, espaços, pontos, hífens, underscores
    sanitized = re.sub(r"[^\w\s.\-]", "", sanitized, flags=re.UNICODE)

    # Remove espaços em branco extras no início e fim
    sanitized = sanitized.strip()

    # Se após sanitização o nome ficou vazio, retorna string vazia
    if not sanitized:
        return ""

    return sanitized


def validate_category(category):
    """
    Verifica se a categoria informada está na lista de categorias válidas.

    Args:
        category: Nome da categoria a ser validada.

    Returns:
        dict com 'valid' (bool) e 'error' (str) caso inválido.
        A mensagem de erro inclui a lista de categorias válidas.
    """
    if not category or not isinstance(category, str):
        return {
            "valid": False,
            "error": (
                "Categoria inválida. "
                f"Categorias válidas: {', '.join(sorted(VALID_CATEGORIES))}"
            ),
        }

    if category.strip().lower() not in VALID_CATEGORIES:
        return {
            "valid": False,
            "error": (
                "Categoria inválida. "
                f"Categorias válidas: {', '.join(sorted(VALID_CATEGORIES))}"
            ),
        }

    return {"valid": True}
