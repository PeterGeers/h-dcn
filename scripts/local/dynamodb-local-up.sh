#!/usr/bin/env bash
#
# dynamodb-local-up.sh — start (or reuse) a DynamoDB Local container for the
# local backend testing (Tier 2) flow.
#
# Part of the `local-backend-testing` spec (T2.3, R7.4).
#
# What it does:
#   - Ensures a named Docker network `hdcn-local` exists so `sam local invoke`
#     containers can reach DynamoDB Local by the hostname `dynamodb-local`
#     (they run with `--docker-network hdcn-local`; handlers use
#     AWS_ENDPOINT_URL_DYNAMODB=http://dynamodb-local:8000).
#   - Starts (or reuses) a container named `dynamodb-local` running
#     `amazon/dynamodb-local`, attached to that network, also publishing port
#     8000 to the host so host-side seeding via http://localhost:8000 works.
#
# Uses the native WSL Docker engine only (Docker Desktop is not a supported
# path for this project).
#
# Idempotent: safe to run repeatedly.

set -euo pipefail

NETWORK="hdcn-local"
CONTAINER="dynamodb-local"
IMAGE="amazon/dynamodb-local"
HOST_PORT="8000"
CONTAINER_PORT="8000"

# 1. Ensure the shared network exists.
if ! docker network inspect "${NETWORK}" >/dev/null 2>&1; then
  echo "Creating Docker network '${NETWORK}'..."
  docker network create "${NETWORK}" >/dev/null
else
  echo "Docker network '${NETWORK}' already exists."
fi

# 2. Start or reuse the container.
if docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
  echo "Container '${CONTAINER}' is already running."
elif docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
  echo "Container '${CONTAINER}' exists but is stopped — starting it..."
  docker start "${CONTAINER}" >/dev/null
else
  echo "Starting new '${CONTAINER}' container from '${IMAGE}'..."
  docker run -d \
    --name "${CONTAINER}" \
    --network "${NETWORK}" \
    --network-alias "${CONTAINER}" \
    -p "${HOST_PORT}:${CONTAINER_PORT}" \
    "${IMAGE}" \
    -jar DynamoDBLocal.jar -sharedDb >/dev/null
fi

echo "DynamoDB Local is up."
echo "  Host endpoint      : http://localhost:${HOST_PORT}"
echo "  In-network endpoint: http://${CONTAINER}:${CONTAINER_PORT} (via '${NETWORK}')"
