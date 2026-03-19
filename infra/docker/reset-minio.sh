#!/usr/bin/env bash
# Reset MinIO storage — removes all uploaded documents and recreates the bucket.
# Usage: bash infra/docker/reset-minio.sh
#
# This stops the MinIO container, deletes its volume, restarts it,
# and waits for the service to be healthy again.
# The app's lifespan handler (ensure_bucket_exists) will recreate the bucket on next API start.

set -euo pipefail

COMPOSE_FILE="infra/docker/docker-compose.yml"
CONTAINER="saldora-minio"

echo "Stopping MinIO..."
docker compose -f "$COMPOSE_FILE" stop minio

echo "Removing MinIO container and volume..."
docker compose -f "$COMPOSE_FILE" rm -f minio
docker volume rm docker_minio_data 2>/dev/null || docker volume rm faktura-ai_minio_data 2>/dev/null || true

echo "Starting MinIO..."
docker compose -f "$COMPOSE_FILE" up -d minio

echo "Waiting for MinIO to be healthy (docker healthcheck interval is 30s)..."
for i in $(seq 1 60); do
    if docker inspect --format='{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null | grep -q healthy; then
        echo "MinIO is ready. Bucket will be recreated on next API start."
        exit 0
    fi
    sleep 1
done

echo "Warning: MinIO did not become healthy within 60 seconds."
echo "Check: docker logs $CONTAINER"
exit 1
