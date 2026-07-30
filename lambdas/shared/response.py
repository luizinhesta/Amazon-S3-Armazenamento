"""
Módulo de resposta HTTP para funções Lambda do Cofre Digital.

Compatível com API Gateway HTTP API payload format version 2.0.
Fornece funções para construir respostas padronizadas e
parsear eventos de entrada.
"""

import json
import base64


# Headers CORS padrão para todas as respostas
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
}


def success_response(body, status=200):
    """
    Constrói uma resposta de sucesso compatível com API Gateway HTTP API v2.0.

    Args:
        body: Dicionário ou lista a ser serializado como JSON.
        status: Código HTTP de status (padrão 200).

    Returns:
        Dicionário com statusCode, headers e body formatados.
    """
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            **CORS_HEADERS,
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }


def error_response(message, code="INTERNAL_ERROR", status=500):
    """
    Constrói uma resposta de erro padronizada.

    Args:
        message: Mensagem de erro em português para o usuário.
        code: Código de erro interno (VALIDATION_ERROR, NOT_FOUND, CONFLICT, INTERNAL_ERROR).
        status: Código HTTP de status.

    Returns:
        Dicionário com statusCode, headers e body formatados.
    """
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            **CORS_HEADERS,
        },
        "body": json.dumps(
            {"error": message, "code": code},
            ensure_ascii=False,
        ),
    }


def parse_body(event):
    """
    Extrai e parseia o body JSON de um evento API Gateway HTTP API v2.0.

    Trata:
        - Body em texto puro (JSON string)
        - Body codificado em base64
        - Body ausente ou vazio

    Args:
        event: Evento recebido pelo Lambda (payload v2.0).

    Returns:
        Dicionário com os dados do body, ou dicionário vazio se não houver body.
    """
    body = event.get("body", "")

    if not body:
        return {}

    # Verifica se o body está codificado em base64
    if event.get("isBase64Encoded", False):
        try:
            body = base64.b64decode(body).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return {}

    # Parseia o JSON
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return {}


def parse_query_params(event):
    """
    Extrai os parâmetros de query string de um evento API Gateway HTTP API v2.0.

    No payload v2.0, os parâmetros já vêm parseados em queryStringParameters.

    Args:
        event: Evento recebido pelo Lambda (payload v2.0).

    Returns:
        Dicionário com os parâmetros de query string, ou vazio se não houver.
    """
    return event.get("queryStringParameters") or {}
