param([ValidateRange(1024, 65535)][int]$Port = 5000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot 'backend/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw '请先运行 ./setup.ps1（离线包使用 ./setup.ps1 -Offline）。' }
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) { throw '请先构建前端。' }
if (-not (Test-Path -LiteralPath 'backend/demo.db')) {
    & $taskPython backend/seed.py
    if ($LASTEXITCODE -ne 0) { throw '演示数据库初始化失败。' }
}
$env:DATABASE_URL = 'sqlite:///' + ((Join-Path $PSScriptRoot 'backend/demo.db') -replace '\\','/')
$env:FLASK_DEBUG = '0'
Push-Location -LiteralPath backend
try { & $taskPython -m flask --app wsgi run --host 127.0.0.1 --port $Port }
finally { Pop-Location }
