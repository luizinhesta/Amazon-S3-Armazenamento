"""
Lambda: cofre-restaurar-documento

Inicia a restauração de documentos arquivados em classes Glacier.
Permite selecionar o tier de recuperação e quantidade de dias.

Variáveis de ambiente:
    DOCUMENT_BUCKET: Nome do bucket de documentos
    PROCESSED_PREFIX: Prefixo dos documentos processados (padrão: processados)
    DEFAULT_RESTORE_DAYS: Dias de disponibilidade padrão (padrão: 2)
"""

import os
import logging

import boto3
from botocore.exceptions import ClientError

# Importa módulos compartilhados
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.response import success_response, error_response, parse_body
from shared.key_builder import is_in_prefix

# Configuração do logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cliente S3
s3_client = boto3.client("s3")

# Variáveis de ambiente
DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET", "")
PROCESSED_PREFIX = os.environ.get("PROCESSED_PREFIX", "processados")
DEFAULT_RESTORE_DAYS = int(os.environ.get("DEFAULT_RESTORE_DAYS", "2"))

# Classes que suportam restauração
GLACIER_CLASSES = {"GLACIER", "DEEP_ARCHIVE"}

# Tiers válidos por classe de armazenamento
VALID_TIERS = {
    "GLACIER": {"Expedited", "Standard", "Bulk"},
    "DEEP_ARCHIVE": {"Standard", "Bulk"},
}


def lambda_handler(event, context):
    """
    Handler principal. Inicia restauração de documento em Glacier.

    Body esperado:
        key: Chave do objeto no S3 (obrigatório)
        tier: Tier de recuperação - Standard, Bulk, Expedited (padrão: Standard)
        days: Quantidade de dias de disponibilidade (padrão: DEFAULT_RESTORE_DAYS)
    """
    try:
        body = parse_body(event)

        # Valida campos
        object_key = body.get("key", "")
        tier = body.get("tier", "Standard")
        days = int(body.get("days", DEFAULT_RESTORE_DAYS))

        if not object_key:
            return error_response(
                "Parâmetro 'key' é obrigatório",
                "VALIDATION_ERROR",
                400,
            )

        # Valida que a key está no prefixo permitido
        if not is_in_prefix(object_key, PROCESSED_PREFIX):
            logger.warning(f"Tentativa de restauração em prefixo não autorizado: {object_key}")
            return error_response(
                "Acesso negado. Somente documentos processados podem ser restaurados",
                "VALIDATION_ERROR",
                403,
            )

        # Valida dias (mínimo 1, máximo 30)
        if days < 1 or days > 30:
            return error_response(
                "Quantidade de dias deve ser entre 1 e 30",
                "VALIDATION_ERROR",
                400,
            )

        # Verifica se o objeto existe e obtém sua classe
        try:
            head_response = s3_client.head_object(
                Bucket=DOCUMENT_BUCKET,
                Key=object_key,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return error_response(
                    "Documento não encontrado",
                    "NOT_FOUND",
                    404,
                )
            raise

        storage_class = head_response.get("StorageClass", "STANDARD")
        restore_status = head_response.get("Restore", "")

        # Verifica se o objeto está em classe Glacier
        if storage_class not in GLACIER_CLASSES:
            return error_response(
                f"Documento está na classe {storage_class}. "
                "Restauração só é necessária para objetos em Glacier ou Deep Archive.",
                "CONFLICT",
                409,
            )

        # Verifica se já há restauração em andamento
        if restore_status and 'ongoing-request="true"' in restore_status:
            return error_response(
                "Restauração já em andamento para este documento. "
                "Aguarde a conclusão.",
                "CONFLICT",
                409,
            )

        # Verifica se já está restaurado
        if restore_status and 'ongoing-request="false"' in restore_status:
            return success_response({
                "message": "Documento já está restaurado e disponível para download",
                "key": object_key,
                "status": "already_restored",
            })

        # Valida o tier para a classe de armazenamento
        valid_tiers = VALID_TIERS.get(storage_class, {"Standard", "Bulk"})
        if tier not in valid_tiers:
            return error_response(
                f"Tier '{tier}' não é válido para {storage_class}. "
                f"Opções válidas: {', '.join(sorted(valid_tiers))}",
                "VALIDATION_ERROR",
                400,
            )

        # Inicia a restauração
        try:
            s3_client.restore_object(
                Bucket=DOCUMENT_BUCKET,
                Key=object_key,
                RestoreRequest={
                    "Days": days,
                    "GlacierJobParameters": {
                        "Tier": tier,
                    },
                },
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "RestoreAlreadyInProgress":
                return error_response(
                    "Restauração já em andamento para este documento",
                    "CONFLICT",
                    409,
                )
            raise

        logger.info(
            f"Restauração iniciada: key={object_key}, "
            f"classe={storage_class}, tier={tier}, dias={days}"
        )

        return success_response({
            "message": f"Restauração iniciada com sucesso. "
                       f"Tier: {tier}, Disponibilidade: {days} dias.",
            "key": object_key,
            "tier": tier,
            "days": days,
            "storageClass": storage_class,
            "status": "restore_initiated",
        })

    except ClientError as e:
        logger.error(f"Erro AWS na restauração: {str(e)}")
        return error_response(
            "Erro ao iniciar restauração do documento",
            "INTERNAL_ERROR",
            500,
        )
    except Exception as e:
        logger.error(f"Erro na restauração: {str(e)}", exc_info=True)
        return error_response(
            "Erro interno ao restaurar documento",
            "INTERNAL_ERROR",
            500,
        )
