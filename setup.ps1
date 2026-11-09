param([switch]$Offline, [string]$Python)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskCacheRoot = Join-Path $PSScriptRoot '.tools/cache'
New-Item -ItemType Directory -Path "$taskCacheRoot/pip", "$taskCacheRoot/npm", "$taskCacheRoot/uv", "$taskCacheRoot/temp" -Force | Out-Null
$env:PIP_CACHE_DIR = Join-Path $taskCacheRoot 'pip'
$env:npm_config_cache = Join-Path $taskCacheRoot 'npm'
$env:UV_CACHE_DIR = Join-Path $taskCacheRoot 'uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PSScriptRoot '.tools/python'
$env:TEMP = Join-Path $taskCacheRoot 'temp'
$env:TMP = $env:TEMP
if (-not (Test-Path -LiteralPath 'backend/.venv/Scripts/python.exe')) {
    if ($Python) {
        & $Python -m venv backend/.venv
    } elseif (Test-Path -LiteralPath 'python-runtime/python.exe') {
        & ./python-runtime/python.exe -m venv backend/.venv
    } elseif (Test-Path -LiteralPath 'D:/CodexDependencies/python/cpython-3.11.16-windows-x86_64-none/python.exe') {
        & 'D:/CodexDependencies/python/cpython-3.11.16-windows-x86_64-none/python.exe' -m venv backend/.venv
    } elseif (Get-Command uv -ErrorAction SilentlyContinue) {
        $taskBasePython = uv python find 3.11 --offline
        if ($LASTEXITCODE -ne 0) { throw '请先安装 Python 3.11，或使用 -Python 指定其完整路径。' }
        & $taskBasePython -m venv backend/.venv
    } else {
        py -3.11 -m venv backend/.venv
    }
    if ($LASTEXITCODE -ne 0) { throw '请先安装 Python 3.11，再运行此脚本。' }
}
$taskPython = Join-Path $PSScriptRoot 'backend/.venv/Scripts/python.exe'
if ($Offline) {
    $taskWheels = Join-Path $PSScriptRoot 'offline-wheels'
    if (-not (Test-Path -LiteralPath $taskWheels)) { $taskWheels = Join-Path $PSScriptRoot 'release/offline-wheels' }
    & $taskPython -m pip install --no-index --find-links $taskWheels -r backend/requirements.txt
} else {
    & $taskPython -m pip install -r backend/requirements.txt
}
if ($LASTEXITCODE -ne 0) { throw '后端依赖安装失败。' }
if (-not $Offline) {
    $taskNodeVersion = node --version
    if ($taskNodeVersion -notmatch '^v20\.') { throw '前端开发需要 Node.js 20。' }
    Push-Location -LiteralPath frontend
    try {
        npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败。' }
        npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw '前端构建失败。' }
    } finally { Pop-Location }
}
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) { throw '缺少网页构建产物；离线运行请使用完整交付包。' }
Write-Host '环境已准备好。运行 ./start-demo.ps1 启动独立演示库。'
