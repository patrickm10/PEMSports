# NFLStatsPro - Service Management Utility
# Usage: 
#   .\scripts\manage_services.ps1 -Action start
#   .\scripts\manage_services.ps1 -Action stop

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart")]
    [string]$Action
)

function Stop-Services {
    Write-Host "Stopping NFLStatsPro services..." -ForegroundColor Yellow
    
    # Ports to clear
    $ports = @(8000, 5173)
    
    foreach ($port in $ports) {
        $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($connections) {
            foreach ($conn in $connections) {
                try {
                    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
                    if ($proc) {
                        Write-Host "Killing process $($proc.Name) (PID: $($proc.Id)) on port $port" -ForegroundColor Cyan
                        Stop-Process -Id $proc.Id -Force
                    }
                } catch {
                    Write-Warning "Could not stop process on port $port"
                }
            }
        }
    }
    
    # Also kill any orphaned python/node processes related to this project
    Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*backend.main*" } | Stop-Process -Force
    Get-Process node -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*nflstats-pro-ui*" } | Stop-Process -Force
}

function Start-Services {
    Write-Host "Starting NFLStatsPro services..." -ForegroundColor Green
    
    # Start Backend
    Write-Host "Launching Backend (FastAPI) on port 8000..." -ForegroundColor Cyan
    $env:PYTHONPATH="src"
    Start-Process python -ArgumentList "-m backend.main" -WindowStyle Normal
    
    # Wait for backend to warm up
    Start-Sleep -Seconds 3
    
    # Start Frontend
    Write-Host "Launching Frontend (Vite) on port 5173..." -ForegroundColor Cyan
    Start-Process npm -ArgumentList "run dev --prefix frontend/nflstats-pro-ui" -WindowStyle Normal
    
    Write-Host "Services launched. Check browser at http://localhost:5173" -ForegroundColor Green
}

switch ($Action) {
    "stop" { Stop-Services }
    "start" { Stop-Services; Start-Services }
    "restart" { Stop-Services; Start-Services }
}
