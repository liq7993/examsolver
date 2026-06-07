# Set these env vars once, or pass -LlamaServer / -ModelPath / -MmprojPath each run:
#   $env:EXAMSOLVER_LLAMA_SERVER       = "<absolute path to llama-server.exe>"
#   $env:EXAMSOLVER_GEMMA4_GGUF_PATH   = "<absolute path to gemma 4 GGUF>"
#   $env:EXAMSOLVER_GEMMA4_MMPROJ_PATH = "<absolute path to gemma 4 mmproj>"
param(
  [string]$LlamaServer = $(if ($env:EXAMSOLVER_LLAMA_SERVER) { $env:EXAMSOLVER_LLAMA_SERVER } else { "llama-server.exe" }),
  [string]$ModelPath = $env:EXAMSOLVER_GEMMA4_GGUF_PATH,
  [string]$MmprojPath = $env:EXAMSOLVER_GEMMA4_MMPROJ_PATH,
  [int]$LlmPort = 8080,
  [int]$AppPort = 8000,
  [switch]$NoBrowser
)

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
$env:EXAMSOLVER_LLM_BASE_URL = "http://127.0.0.1:$LlmPort/v1"
$env:EXAMSOLVER_LLM_MODEL = "gemma-4-E2B-it-Q4_K_M"
$env:EXAMSOLVER_LLM_MODEL_PATH = $ModelPath
$env:EXAMSOLVER_LLM_TIMEOUT_SECONDS = "60"
$env:EXAMSOLVER_LLM_MAX_TOKENS = "256"
$env:NO_PROXY = "127.0.0.1,localhost"
$env:no_proxy = "127.0.0.1,localhost"

$resolvedLlamaServer = Resolve-CommandPath $LlamaServer

if (Test-PortListening $LlmPort) {
  Write-Host "Gemma local LLM already listening on $env:EXAMSOLVER_LLM_BASE_URL"
} elseif ($resolvedLlamaServer) {
  if (!(Test-Path -LiteralPath $ModelPath)) {
    throw "Gemma model file not found: $ModelPath"
  }

  $gemmaLog = Join-Path $repoRoot ".codex-gemma-server.log"
  $gemmaScript = Join-Path $PSScriptRoot "start-gemma4-local-llm.ps1"
  $gemmaArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$gemmaScript`" -LlamaServer `"$resolvedLlamaServer`" -ModelPath `"$ModelPath`" -MmprojPath `"$MmprojPath`" -Port $LlmPort"

  Start-Process powershell -ArgumentList $gemmaArgs -RedirectStandardOutput $gemmaLog -RedirectStandardError "$gemmaLog.err" -WindowStyle Minimized | Out-Null
  Write-Host "Started Gemma local LLM. Log: $gemmaLog"
} else {
  Write-Warning "llama-server was not found. Examsolver will start, but Gemma enhancement will stay disabled until the server is available."
}

if (!$NoBrowser) {
  Start-Process "http://127.0.0.1:$AppPort/"
}

Write-Host "Starting Examsolver on http://127.0.0.1:$AppPort/"
& uv run uvicorn examsolver.api.app:app --host 127.0.0.1 --port $AppPort
