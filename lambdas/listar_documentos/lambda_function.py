"""
Lambda: cofre-listar-documentos

Lista documentos armazenados no prefixo processados/ do bucket.
Retorna metadados, tags e classe de armazenamento de cada objeto.

Variáveis de ambiente:
    DOCUMENT_BUCKET: Nome do bucket de documentos
    PROCESSED_PREFIX: Prefixo dos documentos processados (padrão: processados)
"""

import os
import logging
import urllib.parse

import boto3
from botocore.exceptions import ClientError

# Garante que o diretório da Lambda esteja no path para imports
import sys
LAMBDA_DIR = os.path.dirname(os.path.abspath(__file__))
if LAMBDA_DIR not in sys.path:
    sys.path.insert(0, LAMBDA_DIR)

from shared.response import success_response, error_response, parse_query_params
from shared.key_builder import extract_filename, extract_category

# Configuração do logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cliente S3
s3_client = boto3.client("s3")

# Variáveis de ambiente
DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET", "")
PROCESSED_PREFIX = os.environ.get("PROCESSED_PREFIX", "processados")

# Quantidade máxima de objetos por página
MAX_KEYS = 50


def lambda_handler(event, context):
    """
    Handler principal. Lista documentos processados com metadados e tags.

    Query parameters:
        prefix: Subcategoria opcional (ex: contratos, notas-fiscais)
        page_token: Token de paginação para a próxima página
    """
    try:
        params = parse_query_params(event)
        sub_prefix = params.get("prefix", "")
        page_token = params.get("page_token", "")

        # Constrói o prefixo de busca
        search_prefix = f"{PROCESSED_PREFIX}/"
        if sub_prefix:
            search_prefix = f"{PROCESSED_PREFIX}/{sub_prefix}/"

        logger.info(f"Listando documentos com prefixo: {search_prefix}")

        # Monta os parâmetros da listagem
        list_params = {
            "Bucket": DOCUMENT_BUCKET,
            "Prefix": search_prefix,
            "MaxKeys": MAX_KEYS,
        }

        if page_token:
            list_params["ContinuationToken"] = page_token

        # Lista objetos no bucket
        response = s3_client.list_objects_v2(**list_params)

        # Processa os objetos encontrados
        documents = []
        for obj in response.get("Contents", []):
            key = obj["Key"]

            # Ignora objetos que são apenas prefixos (terminam com /)
            if key.endswith("/"):
                continue

            # Monta informações básicas do documento
            doc = {
                "key": key,
                "name": extract_filename(key),
                "category": extract_category(key),
                "size": obj["Size"],
                "lastModified": obj["LastModified"].isoformat(),
                "storageClass": obj.get("StorageClass", "STANDARD"),
            }

            # Obtém tags do objeto
            doc["tags"] = get_object_tags(key)

            # Obtém metadados e status de restauração
            head_info = get_object_head(key)
            if head_info:
                doc["metadata"] = head_info.get("metadata", {})
                doc["restoreStatus"] = head_info.get("restoreStatus", None)

            documents.append(doc)

        # Monta resposta com paginação
        result = {
            "documents": documents,
            "count": len(documents),
            "nextPageToken": response.get("NextContinuationToken"),
        }

        if not documents:
            result["message"] = "Nenhum documento encontrado neste prefixo"

        logger.info(f"Retornando {len(documents)} documentos")
        return success_response(result)

    except Exception as e:
        logger.error(f"Erro ao listar documentos: {str(e)}", exc_info=True)
        return error_response(
            "Erro interno ao listar documentos",
            "INTERNAL_ERROR",
            500,
        )


def get_object_tags(key):
    """
    Obtém as tags de um objeto S3.

    Returns:
        Dicionário com as tags do objeto, ou vazio em caso de erro.
    """
    try:
        response = s3_client.get_object_tagging(
            Bucket=DOCUMENT_BUCKET,
            Key=key,
        )
        tags = {}
        for tag in response.get("TagSet", []):
            tags[tag["Key"]] = tag["Value"]
        return tags
    except ClientError:
        return {}


def get_object_head(key):
    """
    Obtém metadados e status de restauração de um objeto S3.

    Returns:
        Dicionário com metadata e restoreStatus, ou None em caso de erro.
    """
    try:
        response = s3_client.head_object(
            Bucket=DOCUMENT_BUCKET,
            Key=key,
        )
        return {
            "metadata": response.get("Metadata", {}),
            "restoreStatus": response.get("Restore"),
        }
    except ClientError:
        return None
