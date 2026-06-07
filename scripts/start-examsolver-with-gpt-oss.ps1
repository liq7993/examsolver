# Set these env vars once, or pass -LlamaServer / -ModelPath each run:
#   $env:EXAMSOLVER_LLAMA_SERVER     = "<absolute path to llama-server.exe>"
#   $env:EXAMSOLVER_GPT_OSS_20B_PATH = "<absolute path to gpt-oss-20b GGUF>"
param(
  [string]$LlamaServer = $(if ($env:EXAMSOLVER_LLAMA_SERVER) { $env:EXAMSOLVER_LLAMA_SERVER } else { "llama-server.exe" }),
  [string]$ModelPath = $env:EXAMSOLVER_GPT_OSS_20B_PATH,
  [int]$LlmPort = 8080,
  [int]$AppPort = 8000,
  [int]$ContextSize = 32768,
  [switch]$NoBrowser
)

# One-shot startup: local GPT-OSS 20B (via llama-server) + Examsolver FastAPI.
# Mirrors start-examsolver-with-gemma.ps1 but for the GPT-OSS preset.
# Switch between the two by running the matching script.

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

function Test-PortListening([int]$Port) {
  $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  return $null -ne $connection
}

function Resolve-CommandPath([string]$Command) {
  $resolved = Get-Command $Command -ErrorAction SilentlyContinue
  if ($resolved) {
    return $resolved.Source
  }
  if (Test-Path -LiteralPath $Command) {
    return (Resolve-Path -LiteralPath $Command).Path
  }
  return $null
}

$env:EXAMSOLVER_LLM_PROVIDER = "local_gguf"
$env:EXAMSOLVER_LLM_PRESET = "gpt-oss-20b"
$env:EXAMSOLVER_LLM_BASE_URL = "http://127.0.0.1:$LlmPort/v1"
$env:EXAMSOLVER_LLM_MODEL = "gpt-oss-20b"
$env:EXAMSOLVER_LLM_MODEL_PATH = $ModelPath
$env:EXAMSOLVER_LLM_TIMEOUT_SECONDS = "120"
$env:EXAMSOLVER_LLM_MAX_TOKENS = "1024"
$env:NO_PROXY = "127.0.0.1,localhost"
$env:no_proxy = "127.0.0.1,localhost"

$resolvedLlamaServer = Resolve-CommandPath $LlamaServer

if (Test-PortListening $LlmPort) {
  Write-Host "Local LLM already listening on $env:EXAMSOLVER_LLM_BASE_URL"
} elseif ($resolvedLlamaServer) {
  if (!(Test-Path -LiteralPath $ModelPath)) {
    throw @"
GPT-OSS GGUF not found at: $ModelPath

See docs/gpt-oss-setup.md for acquisition. Falling back to Gemma is one
command away: .\scripts\start-examsolver-with-gemma.ps1
"@
  }

  $serverLog = Join-Path $repoRoot ".gpt-oss-server.log"
  $modelScript = Join-Path $PSScriptRoot "start-gpt-oss-local-llm.ps1"
  $modelArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$modelScript`" -LlamaServer `"$resolvedLlamaServer`" -ModelPath `"$ModelPath`" -Port $LlmPort -ContextSize $ContextSize"

  Start-Process powershell -ArgumentList $modelArgs -RedirectStandardOutput $serverLog -RedirectStandardError "$serverLog.err" -WindowStyle Minimized | Out-Null
  Write-Host "Started GPT-OSS local LLM. Log: $serverLog"
} else {
  Write-Warning "llama-server was not found. Examsolver will start, but local LLM will stay disabled until the server is available."
}

if (!$NoBrowser) {
  Start-Process "http://127.0.0.1:$AppPort/"
}

Write-Host "Starting Examsolver on http://127.0.0.1:$AppPort/"
& uv run uvicorn examsolver.api.app:app --host 127.0.0.1 --port $AppPort
