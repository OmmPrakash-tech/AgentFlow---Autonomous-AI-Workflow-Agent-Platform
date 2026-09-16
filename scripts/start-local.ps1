param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('api', 'engine', 'frontend')]
    [string]$Service
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$configPath = Join-Path $projectRoot '.env.local'
if (-not (Test-Path -LiteralPath $configPath)) {
    throw 'Create .env.local with your native PostgreSQL and application settings first. See docs/deployment.md.'
}
foreach ($line in Get-Content -LiteralPath $configPath) {
    if ($line -match '^\s*#' -or [string]::IsNullOrWhiteSpace($line)) { continue }
    $parts = $line.Split('=', 2)
    if ($parts.Count -ne 2 -or $parts[0] -notmatch '^[A-Z][A-Z0-9_]*$') { throw 'Invalid local configuration entry.' }
    [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
}
Push-Location $projectRoot
try {
    switch ($Service) {
        'api' {
            $java = if ($env:JAVA_HOME) { Join-Path $env:JAVA_HOME 'bin/java.exe' } else { 'java' }
            & $java -jar (Join-Path $projectRoot 'backend/target/backend-0.1.0.jar')
        }
        'engine' {
            Set-Location (Join-Path $projectRoot 'agent-engine')
            & '.venv/Scripts/python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
        }
        'frontend' {
            Set-Location (Join-Path $projectRoot 'frontend')
            & node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5174 --strictPort
        }
    }
    if ($LASTEXITCODE -ne 0) { throw "$Service exited with code $LASTEXITCODE" }
} finally {
    Pop-Location
}
