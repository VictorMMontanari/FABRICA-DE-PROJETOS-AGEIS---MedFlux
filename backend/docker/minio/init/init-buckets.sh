#!/bin/sh
# Cria os buckets do MedFlux no MinIO (idempotente). Executado pelo serviço minio-init do compose.
set -eu

: "${MINIO_URL:=http://minio:9000}"
: "${MINIO_ACCESS_KEY:?MINIO_ACCESS_KEY não definido}"
: "${MINIO_SECRET_KEY:?MINIO_SECRET_KEY não definido}"
: "${MINIO_BUCKET:=medflux-documents}"

echo "Aguardando MinIO em ${MINIO_URL}..."
until mc alias set medflux "${MINIO_URL}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" >/dev/null 2>&1; do
  sleep 2
done

for bucket in medflux-users medflux-triage "${MINIO_BUCKET}"; do
  mc mb --ignore-existing "medflux/${bucket}"
  # Buckets privados: o acesso é feito por URL pré-assinada ou pelo endpoint autenticado do backend.
  mc anonymous set none "medflux/${bucket}" >/dev/null
done

echo "Buckets prontos:"
mc ls medflux
