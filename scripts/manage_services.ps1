# NFLStatsPro - Service Management Utility (delegates to manage_services.py)
# Usage:
#   .\scripts\manage_services.ps1 -Action start
#   .\scripts\manage_services.ps1 -Action stop
#   .\scripts\manage_services.ps1 -Action restart

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart")]
    [string]$Action
)

$py = Join-Path $PSScriptRoot "manage_services.py"
if (-not (Test-Path $py)) {
    Write-Error "Missing $py"
    exit 1
}

python $py $Action
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
