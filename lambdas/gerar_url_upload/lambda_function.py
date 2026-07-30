"""
Lambda: cofre-gerar-url-upload

Gera uma URL pré-assinada para upload de documentos diretamente ao S3.
O arquivo é enviado pelo navegador direto ao bucket, sem passar pelo Lambda.

Variáveis de ambiente:
    DOCUMENT_BUCKET: Nome do bucket de documentos
    UPLOAD_PREFIX: Prefixo de destino (padrão: entrada)
    URL_EXPIRATION_SECONDS: Tempo de validade da URL (padrão: 300)
    MAX_FILE_SIZE_MB: Tamanho máximo em MB (padrão: 20)
"""

import os
import json
import logging
import boto3
from datetime import datetime, timezone

# Importa módulos compartilhados
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.validation import (
    validate_extension,
    validate_required_fields,
    validate_category,
    sanitize_filename,
    MAX_FILE_SIZE_MB as DEFAULT_MAX_SIZE,
)
from shared.key_builder import build_upload_key
from shared.response import success_response, error_response, parse_body

# Configuração do logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cliente S3
s3_client = boto3.client("s3")

# Variáveis de ambiente
DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET", "")
UPLOAD_PREFIX = os.environ.get("UPLOAD_PREFIX", "entrada")
URL_EXPIRATION_SECONDS = int(os.environ.get("URL_EXPIRATION_SECONDS", "300"))
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", str(DEFAULT_MAX_SIZE)))


def lambda_handler(event, context):
    """
    Handler principal. Recebe requisição POST com dados do documento
    e retorna URL pré-assinada para upload.

    Body esperado:
        filename: Nome do arquivo original
        category: Categoria do documento (contratos, notas-fiscais, etc.)
        contentType: MIME type do arquivo
        documentName: Nome descritivo do documento (opcional)
        documentType: Tipo do documento (opcional)
        description: Descrição do documento (opcional)
        fileSize: Tamanho do arquivo em bytes (opcional, validado se informado)
    """
    try:
        logger.info("Recebendo solicitação de URL para upload")

        # Parseia o body da requisição
        body = parse_body(event)

        # Valida campos obrigatórios
        validation = validate_required_fields(body, ["filename", "category", "contentType"])
        if not validation["valid"]:
            logger.warning(f"Campos obrigatórios ausentes: {validation['missing_fields']}")
            return error_response(validation["error"], "VALIDATION_ERROR", 400)

        filename = body["filename"]
        category = body["category"]
        content_type = body["contentType"]
        file_size = body.get("fileSize", 0)

        # Valida extensão do arquivo
        ext_validation = validate_extension(filename)
        if not ext_validation["valid"]:
            logger.warning(f"Extensão inválida para arquivo: {filename}")
            return error_response(ext_validation["error"], "VALIDATION_ERROR", 400)

        # Valida categoria
        cat_validation = validate_category(category)
        if not cat_validation["valid"]:
            logger.warning(f"Categoria inválida: {category}")
            return error_response(cat_validation["error"], "VALIDATION_ERROR", 400)

        # Valida tamanho se informado
        max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size and int(file_size) > max_size_bytes:
            msg = f"Arquivo excede o tamanho máximo de {MAX_FILE_SIZE_MB}MB"
            logger.warning(msg)
            return error_response(msg, "VALIDATION_ERROR", 400)

        # Sanitiza o nome do arquivo
        safe_filename = sanitize_filename(filename)
        if not safe_filename:
            return error_response(
                "Nome do arquivo inválido após sanitização",
                "VALIDATION_ERROR",
                400,
            )

        # Constrói a chave S3
        object_key = build_upload_key(UPLOAD_PREFIX, category, safe_filename)

        # Metadados do documento
        metadata = {
            "nome-documento": body.get("documentName", safe_filename),
            "tipo-documento": body.get("documentType", category),
            "descricao": body.get("description", ""),
            "data-upload": datetime.now(timezone.utc).isoformat(),
            "origem": "cofre-digital",
        }

        # Gera URL pré-assinada para PUT
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": DOCUMENT_BUCKET,
                "Key": object_key,
                "ContentType": content_type,
                "Metadata": metadata,
            },
            ExpiresIn=URL_EXPIRATION_SECONDS,
        )

        logger.info(f"URL de upload gerada para key: {object_key}")

        # Retorna resposta com URL e informações necessárias para o frontend
        return success_response({
            "uploadUrl": presigned_url,
            "key": object_key,
            "expiresIn": URL_EXPIRATION_SECONDS,
            "headers": {
                "Content-Type": content_type,
                "x-amz-meta-nome-documento": metadata["nome-documento"],
                "x-amz-meta-tipo-documento": metadata["tipo-documento"],
                "x-amz-meta-descricao": metadata["descricao"],
                "x-amz-meta-data-upload": metadata["data-upload"],
                "x-amz-meta-origem": metadata["origem"],
            },
        })

    except Exception as e:
        logger.error(f"Erro ao gerar URL de upload: {str(e)}", exc_info=True)
        return error_response(
            "Erro interno ao gerar URL de upload",
            "INTERNAL_ERROR",
            500,
        )
