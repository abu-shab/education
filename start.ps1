$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$academiaPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $academiaPython)) {
    Write-Host 'Create the Python 3.12 environment first; see README.md.'
    exit 1
}
Write-Host 'ACADEMIA AI - open http://127.0.0.1:8000 after startup. Ctrl+C stops the server.'
& $academiaPython -m uvicorn app:app --host 127.0.0.1 --port 8000 --no-access-log
