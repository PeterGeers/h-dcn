#!/usr/bin/env bash
#
# dynamodb-local-down.sh — stop and remove the DynamoDB Local container used by
# the local backend testing (Tier 2) flow.
#
# Part of the `local-backend-testing` spec (T2.3, R7.4).
#
# What it does:
#   - Stops and removes the `dynamodb-local` container (idempotent — no error if
#     it is already gone).
#
# Network choice: the shared `hdcn-local` network is intentionally LEFT IN PLACE.
# It is cheap, harmless, and is reused by `sam local invoke --docker-network
# hdcn-local`. Removing it would fail while other containers are still attached
# and would just have to be recreated on the next `-up`. Keeping it is the
# simplest, safest choice. Remove it manually with `docker network rm hdcn-local`
# if you really want a clean slate.
#
# Uses the native WSL Docker engine only.
#
# Idempotent: safe to run repeatedly.

set -euo pipefail

CONTAINER="dynamodb-local"

if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
  echo "Stopping and removing container '${CONTAINER}'..."
  docker rm -f "${CONTAINER}" >/dev/null
  echo "Container '${CONTAINER}' removed."
else
  echo "Container '${CONTAINER}' not present — nothing to tear down."
fi
