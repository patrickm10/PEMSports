# Smoke-test production endpoints (Render backend + pemsports.com frontend).
# Usage: .\scripts\verify_production.ps1
# Override defaults: $env:PROD_API="https://..."; $env:PROD_FRONTEND="https://..."

$ErrorActionPreference = "Stop"

$ApiBase = if ($env:PROD_API) { $env:PROD_API.TrimEnd("/") } else { "https://nflstats-api.onrender.com" }
$Frontend = if ($env:PROD_FRONTEND) { $env:PROD_FRONTEND.TrimEnd("/") } else { "https://pemsports.com" }
$Origin = $Frontend

Write-Host "=== Production verification ===" -ForegroundColor Cyan
Write-Host "API:      $ApiBase"
Write-Host "Frontend: $Frontend"
Write-Host ""

$failed = 0

function Test-Step {
    param([string]$Name, [scriptblock]$Block)
    Write-Host "[$Name] " -NoNewline
    try {
        & $Block
        Write-Host "OK" -ForegroundColor Green
    } catch {
        Write-Host "FAIL: $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
    }
}

Test-Step "Render /health returns 200" {
    $r = Invoke-WebRequest -Uri "$ApiBase/health" -UseBasicParsing -TimeoutSec 60
    if ($r.StatusCode -ne 200) { throw "HTTP $($r.StatusCode)" }
    $body = $r.Content | ConvertFrom-Json
    if (-not $body.status) { throw "Missing status field" }
}

Test-Step "Rankings endpoint returns JSON array" {
    $r = Invoke-WebRequest -Uri "$ApiBase/api/v1/rankings/QB?year=2024&limit=3" -UseBasicParsing -TimeoutSec 60
    if ($r.StatusCode -ne 200) { throw "HTTP $($r.StatusCode)" }
    $rows = $r.Content | ConvertFrom-Json
    if ($rows -isnot [Array] -or $rows.Count -lt 1) { throw "Expected non-empty JSON array" }
    if (-not $rows[0].player_name) { throw "Missing player_name in first row" }
}

Test-Step "CORS preflight allows frontend origin" {
    $headers = @{
        Origin = $Origin
        "Access-Control-Request-Method" = "GET"
        "Access-Control-Request-Headers" = "Content-Type"
    }
    $r = Invoke-WebRequest -Uri "$ApiBase/api/v1/rankings/QB/seasons" -Method Options -Headers $headers -UseBasicParsing -TimeoutSec 60
    $allowOrigin = $r.Headers["Access-Control-Allow-Origin"]
    if (-not $allowOrigin) { throw "No Access-Control-Allow-Origin header" }
    if ($allowOrigin -ne $Origin -and $allowOrigin -ne "*") {
        throw "Access-Control-Allow-Origin=$allowOrigin (expected $Origin)"
    }
}

Test-Step "Frontend loads publicly" {
    $r = Invoke-WebRequest -Uri "$Frontend/" -UseBasicParsing -TimeoutSec 60
    if ($r.StatusCode -ne 200) { throw "HTTP $($r.StatusCode)" }
    if ($r.Content -notmatch "html") { throw "Response does not look like HTML" }
    if ($r.Content -match "FUNCTION_INVOCATION_FAILED") { throw "Vercel serverless error page" }
}

Test-Step "Frontend bundle references Render API (not localhost)" {
    $r = Invoke-WebRequest -Uri "$Frontend/" -UseBasicParsing -TimeoutSec 60
    $assetMatch = [regex]::Match($r.Content, '/assets/index-[^"]+\.js')
    if (-not $assetMatch.Success) { throw "Could not find main JS bundle in index.html" }
    $js = Invoke-WebRequest -Uri "$Frontend$($assetMatch.Value)" -UseBasicParsing -TimeoutSec 60
    if ($js.Content -match "localhost:8000") { throw "Bundle still references localhost:8000" }
    if ($js.Content -match "placeholder\.onrender\.com") { throw "Bundle still references placeholder.onrender.com" }
    $hostOnly = ([uri]$ApiBase).Host
    if ($js.Content -notmatch [regex]::Escape($hostOnly)) {
        throw "Bundle does not reference $hostOnly - check VITE_API_BASE on Vercel"
    }
}

Write-Host ""
if ($failed -eq 0) {
    Write-Host "All checks passed." -ForegroundColor Green
    exit 0
}
Write-Host "$failed check(s) failed." -ForegroundColor Red
exit 1
