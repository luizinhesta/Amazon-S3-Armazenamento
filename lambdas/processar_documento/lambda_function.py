"""
Lambda: cofre-processar-documento

Processa documentos enviados ao prefixo entrada/ do bucket.
Disparada automaticamente via S3 Event Notification (ObjectCreated).

Fluxo:
    1. Recebe evento S3 com bucket e key
    2. Verifica se está no prefixo correto (prevenção de loop)
    3. Valida extensão do arquivo
    4. Se válido: adiciona tags, copia para processados/, remove original
    5. Se inválido: copia para rejeitados/, remove original

Variáveis de ambiente:
    DOCUMENT_BUCKET: Nome do bucket de documentos
    SOURCE_PREFIX: Prefixo de origem (padrão: entrada)
    PROCESSED_PREFIX: Prefixo de destino para válidos (padrão: processados)
    REJECTED_PREFIX: Prefixo de destino para inválidos (padrão: rejeitados)
"""

import os
import logging
import urllib.parse
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

# Garante que o diretório da Lambda esteja no path para imports
import sys
LAMBDA_DIR = os.path.dirname(os.path.abspath(__file__))
if LAMBDA_DIR not in sys.path:
    sys.path.insert(0, LAMBDA_DIR)

from shared.validation import validate_extension, ALLOWED_EXTENSIONS
from shared.key_builder import (
    build_processed_key,
    build_rejected_key,
    extract_filename,
    extract_category,
    is_in_prefix,
    decode_s3_key,
)

# Configuração do logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cliente S3
s3_client = boto3.client("s3")

# Variáveis de ambiente
DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET", "")
SOURCE_PREFIX = os.environ.get("SOURCE_PREFIX", "entrada")
PROCESSED_PREFIX = os.environ.get("PROCESSED_PREFIX", "processados")
REJECTED_PREFIX = os.environ.get("REJECTED_PREFIX", "rejeitados")

# Tamanho máximo aceitável (20MB)
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

# Regras de tags por categoria
TAG_RULES = {
    "contratos": {"tipo": "contrato", "retencao": "longa", "status": "processado", "projeto": "cofre-digital"},
    "notas-fiscais": {"tipo": "nota-fiscal", "retencao": "legal", "status": "processado", "projeto": "cofre-digital"},
    "relatorios": {"tipo": "relatorio", "retencao": "media", "status": "processado", "projeto": "cofre-digital"},
    "comprovantes": {"tipo": "comprovante", "retencao": "media", "status": "processado", "projeto": "cofre-digital"},
    "outros": {"tipo": "outro", "retencao": "media", "status": "processado", "projeto": "cofre-digital"},
}


def lambda_handler(event, context):
    """
    Handler principal. Processa eventos S3 ObjectCreated.
    """
    try:
        # Processa cada registro do evento S3
        for record in event.get("Records", []):
            process_record(record)

        return {"statusCode": 200, "body": "Processamento concluído"}

    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}", exc_info=True)
        raise


def process_record(record):
    """
    Processa um único registro de evento S3.
    """
    # Extrai informações do evento
    bucket = record["s3"]["bucket"]["name"]
    raw_key = record["s3"]["object"]["key"]

    # Decodifica a chave (S3 codifica caracteres especiais)
    key = decode_s3_key(raw_key)

    logger.info(f"Processando objeto: bucket={bucket}, key={key}")

    # GUARD CLAUSE: Prevenção de loop
    # Só processa objetos no prefixo de entrada
    if not is_in_prefix(key, SOURCE_PREFIX):
        logger.info(f"Ignorando objeto fora do prefixo '{SOURCE_PREFIX}/': {key}")
        return

    # Verifica se o objeto ainda existe (pode já ter sido processado)
    try:
        head_response = s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            logger.info(f"Objeto não encontrado (já processado?): {key}")
            return
        raise

    # Extrai informações do objeto
    file_size = head_response.get("ContentLength", 0)
    content_type = head_response.get("ContentType", "")
    metadata = head_response.get("Metadata", {})

    # Extrai nome do arquivo e valida extensão
    filename = extract_filename(key)
    ext_validation = validate_extension(filename)

    if ext_validation["valid"] and file_size <= MAX_FILE_SIZE_BYTES:
        # Documento válido → processar
        process_valid_document(bucket, key, filename, metadata, content_type)
    else:
        # Documento inválido → rejeitar
        reason = "extensão inválida" if not ext_validation["valid"] else "tamanho excedido"
        process_invalid_document(bucket, key, filename, reason)


def process_valid_document(bucket, key, filename, metadata, content_type):
    """
    Processa um documento válido: copia para processados/ e remove o original.
    """
    # Define chave de destino
    dest_key = build_processed_key(key, PROCESSED_PREFIX)
    category = extract_category(key)

    logger.info(f"Documento válido. Copiando {key} → {dest_key}")

    # Define tags baseadas na categoria
    tags = TAG_RULES.get(category, TAG_RULES["outros"]).copy()
    tags["data-processamento"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Copia o objeto para processados/ preservando metadados
    copy_source = {"Bucket": bucket, "Key": key}

    s3_client.copy_object(
        CopySource=copy_source,
        Bucket=bucket,
        Key=dest_key,
        MetadataDirective="COPY",
        TaggingDirective="REPLACE",
        Tagging=urllib.parse.urlencode(tags),
    )

    logger.info(f"Objeto copiado para: {dest_key}")

    # Remove o objeto original do prefixo de entrada
    s3_client.delete_object(Bucket=bucket, Key=key)
    logger.info(f"Objeto original removido: {key}")


def process_invalid_document(bucket, key, filename, reason):
    """
    Processa um documento inválido: copia para rejeitados/ e remove o original.
    """
    dest_key = build_rejected_key(key, REJECTED_PREFIX)

    logger.warning(f"Documento rejeitado ({reason}): {key} → {dest_key}")

    # Tags para documento rejeitado
    tags = {
        "status": "rejeitado",
        "motivo": reason,
        "data-processamento": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "projeto": "cofre-digital",
    }

    # Copia para rejeitados/
    copy_source = {"Bucket": bucket, "Key": key}

    s3_client.copy_object(
        CopySource=copy_source,
        Bucket=bucket,
        Key=dest_key,
        MetadataDirective="COPY",
        TaggingDirective="REPLACE",
        Tagging=urllib.parse.urlencode(tags),
    )

    # Remove o original
    s3_client.delete_object(Bucket=bucket, Key=key)
    logger.info(f"Objeto rejeitado movido e original removido: {key}")
