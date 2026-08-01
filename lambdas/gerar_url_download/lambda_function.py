"""
Lambda: cofre-gerar-url-download

Gera uma URL pré-assinada para download de documentos do S3.
Verifica a classe de armazenamento e o status de restauração antes de gerar.

Variáveis de ambiente:
    DOCUMENT_BUCKET: Nome do bucket de documentos
    PROCESSED_PREFIX: Prefixo dos documentos processados (padrão: processados)
    URL_EXPIRATION_SECONDS: Tempo de validade da URL (padrão: 300)
"""

import os
import logging

import boto3
from botocore.exceptions import ClientError

# Garante que o diretório da Lambda esteja no path para imports
import sys
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

# Classes que requerem restauração antes do download
GLACIER_CLASSES = {"GLACIER", "DEEP_ARCHIVE", "GLACIER_IR"}


def lambda_handler(event, context):
    """
    Handler principal. Gera URL pré-assinada para download.

    Query parameters:
        key: Chave do objeto no S3 (obrigatório)
        versionId: ID de uma versão específica (opcional)
    """
    try:
        params = parse_query_params(event)
        object_key = params.get("key", "")
        version_id = params.get("versionId", "")

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
                "Acesso negado. Somente documentos processados podem ser baixados",
                "VALIDATION_ERROR",
                403,
            )

        # Verifica se o objeto existe e obtém metadados
        try:
            head_params = {"Bucket": DOCUMENT_BUCKET, "Key": object_key}
            if version_id:
                head_params["VersionId"] = version_id

            head_response = s3_client.head_object(**head_params)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return error_response(
                    "Documento não encontrado",
                    "NOT_FOUND",
                    404,
                )
            raise

        # Verifica classe de armazenamento
        storage_class = head_response.get("StorageClass", "STANDARD")
        restore_status = head_response.get("Restore", "")

        # Se está em classe Glacier, verifica restauração
        if storage_class in GLACIER_CLASSES:
            if not restore_status:
                # Sem restauração iniciada
                return error_response(
                    f"Documento arquivado em {storage_class}. "
                    "É necessário solicitar restauração antes do download.",
                    "CONFLICT",
                    409,
                )

            if 'ongoing-request="true"' in restore_status:
                # Restauração em andamento
                return error_response(
                    "Restauração em andamento. Tente novamente mais tarde.",
                    "CONFLICT",
                    409,
                )

            # Se chegou aqui, restore_status contém 'ongoing-request="false"'
            # O objeto está temporariamente disponível
            logger.info(f"Objeto restaurado temporariamente: {object_key}")

        # Gera URL pré-assinada para download
        presigned_params = {
            "Bucket": DOCUMENT_BUCKET,
            "Key": object_key,
        }
        if version_id:
            presigned_params["VersionId"] = version_id

        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params=presigned_params,
            ExpiresIn=URL_EXPIRATION_SECONDS,
        )

        logger.info(f"URL de download gerada para: {object_key}")

        return success_response({
            "downloadUrl": download_url,
            "key": object_key,
            "expiresIn": URL_EXPIRATION_SECONDS,
            "storageClass": storage_class,
        })

    except ClientError as e:
        logger.error(f"Erro AWS ao gerar URL de download: {str(e)}")
        return error_response(
            "Erro ao acessar o documento",
            "INTERNAL_ERROR",
            500,
        )
    except Exception as e:
        logger.error(f"Erro ao gerar URL de download: {str(e)}", exc_info=True)
        return error_response(
            "Erro interno ao gerar URL de download",
            "INTERNAL_ERROR",
            500,
        )
