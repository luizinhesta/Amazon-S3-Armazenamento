"""
Lambda: cofre-listar-versoes

Lista todas as versões de um documento específico no S3.
Utiliza list_object_versions para retornar histórico completo.

Variáveis de ambiente:
    DOCUMENT_BUCKET: Nome do bucket de documentos
    PROCESSED_PREFIX: Prefixo dos documentos processados (padrão: processados)
    URL_EXPIRATION_SECONDS: Tempo de validade da URL (padrão: 300)
"""

import os
import sys
import logging

import boto3
from botocore.exceptions import ClientError

# Garante que o diretório da Lambda esteja no path para imports
# (necessário quando shared/ está no mesmo nível que lambda_function.py)
LAMBDA_DIR = os.path.dirname(os.path.abspath(__file__))
if LAMBDA_DIR not in sys.path:
    sys.path.insert(0, LAMBDA_DIR)

from shared.response import success_response, error_response, parse_query_params
from shared.key_builder import is_in_prefix

# Configuração do logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cliente S3
s3_client = boto3.client("s3")

# Variáveis de ambiente
DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET", "")
PROCESSED_PREFIX = os.environ.get("PROCESSED_PREFIX", "processados")
URL_EXPIRATION_SECONDS = int(os.environ.get("URL_EXPIRATION_SECONDS", "300"))


def lambda_handler(event, context):
    """
    Handler principal. Lista versões de um documento.

    Query parameters:
        key: Chave do objeto no S3 (obrigatório)
        download_version: ID da versão para gerar URL de download (opcional)
    """
    try:
        params = parse_query_params(event)
        object_key = params.get("key", "")
        download_version = params.get("download_version", "")

        # Valida presença da key
        if not object_key:
            return error_response(
                "Parâmetro 'key' é obrigatório",
                "VALIDATION_ERROR",
                400,
            )

        # Valida que a key está no prefixo permitido
        if not is_in_prefix(object_key, PROCESSED_PREFIX):
            logger.warning(f"Tentativa de acesso a prefixo não autorizado: {object_key}")
            return error_response(
                "Acesso negado. Somente documentos processados podem ser consultados",
                "VALIDATION_ERROR",
                403,
            )

        # Se solicitou download de versão específica, gera URL
        if download_version:
            return generate_version_download(object_key, download_version)

        # Lista versões do objeto
        response = s3_client.list_object_versions(
            Bucket=DOCUMENT_BUCKET,
            Prefix=object_key,
        )

        # Processa versões (exclui delete markers da lista principal)
        versions = []
        for version in response.get("Versions", []):
            # Filtra apenas versões do objeto exato (evita subprefixos)
            if version["Key"] != object_key:
                continue

            versions.append({
                "versionId": version["VersionId"],
                "lastModified": version["LastModified"].isoformat(),
                "size": version["Size"],
                "isLatest": version["IsLatest"],
                "storageClass": version.get("StorageClass", "STANDARD"),
            })

        # Processa delete markers separadamente
        delete_markers = []
        for marker in response.get("DeleteMarkers", []):
            if marker["Key"] != object_key:
                continue

            delete_markers.append({
                "versionId": marker["VersionId"],
                "lastModified": marker["LastModified"].isoformat(),
                "isLatest": marker["IsLatest"],
                "isDeleteMarker": True,
            })

        logger.info(f"Encontradas {len(versions)} versões para: {object_key}")

        return success_response({
            "key": object_key,
            "versions": versions,
            "deleteMarkers": delete_markers,
            "totalVersions": len(versions),
        })

    except ClientError as e:
        logger.error(f"Erro AWS ao listar versões: {str(e)}")
        return error_response(
            "Erro ao consultar versões do documento",
            "INTERNAL_ERROR",
            500,
        )
    except Exception as e:
        logger.error(f"Erro ao listar versões: {str(e)}", exc_info=True)
        return error_response(
            "Erro interno ao listar versões",
            "INTERNAL_ERROR",
            500,
        )


def generate_version_download(object_key, version_id):
    """
    Gera URL pré-assinada para download de uma versão específica.
    """
    try:
        # Verifica se a versão existe
        s3_client.head_object(
            Bucket=DOCUMENT_BUCKET,
            Key=object_key,
            VersionId=version_id,
        )

        # Gera URL pré-assinada
        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": DOCUMENT_BUCKET,
                "Key": object_key,
                "VersionId": version_id,
            },
            ExpiresIn=URL_EXPIRATION_SECONDS,
        )

        logger.info(f"URL de download gerada para versão {version_id} de {object_key}")

        return success_response({
            "downloadUrl": download_url,
            "key": object_key,
            "versionId": version_id,
            "expiresIn": URL_EXPIRATION_SECONDS,
        })

    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return error_response(
                "Versão não encontrada",
                "NOT_FOUND",
                404,
            )
        raise
