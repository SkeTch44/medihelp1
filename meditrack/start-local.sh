#!/usr/bin/env sh
set -eu
if [ ! -f .env ]; then
  cp .env.example .env
  echo 'Created .env. Set JWT_SECRET before running again.'
  exit 0
fi
docker compose -f infra/docker-compose.yml up --build
