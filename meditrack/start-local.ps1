$ErrorActionPreference = 'Stop'
if (-not (Test-Path '.env')) {
  Copy-Item '.env.example' '.env'
  Write-Host 'Created .env from .env.example. Edit JWT_SECRET before continuing.' -ForegroundColor Yellow
  Write-Host 'Then run this script again.'
  exit 0
}
docker compose -f infra/docker-compose.yml up --build
