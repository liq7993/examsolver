# Defaults read from env vars (see start-examsolver-with-gemma.ps1 header for names).
param(
  [string]$LlamaServer = $(if ($env:EXAMSOLVER_LLAMA_SERVER) { $env:EXAMSOLVER_LLAMA_SERVER } else { "llama-server.exe" }),
  [string]$ModelPath = $env:EXAMSOLVER_GEMMA4_GGUF_PATH,
  [string]$MmprojPath = $env:EXAMSOLVER_GEMMA4_MMPROJ_PATH,
  [int]$Port = 8080,
  [int]$ContextSize = 8192,
  [int]$GpuLayers = 999
)

$ErrorActionPreference = "Stop"

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

$resolvedLlamaServer = Resolve-CommandPath $LlamaServer
if (!$resolvedLlamaServer) {
  throw "Cannot find llama-server: $LlamaServer"
}

if (!(Test-Path -LiteralPath $ModelPath)) {
  throw "Model file not found: $ModelPath"
}

$arguments = @(
  "--model", $ModelPath,
  "--host", "127.0.0.1",
  "--port", [string]$Port,
  "--ctx-size", [string]$ContextSize,
  "--n-gpu-layers", [string]$GpuLayers
)

if (Test-Path -LiteralPath $MmprojPath) {
  $arguments += @("--mmproj", $MmprojPath)
}

Write-Host "Starting Gemma 4 local LLM on http://127.0.0.1:$Port/v1"
Write-Host "Model: $ModelPath"
& $resolvedLlamaServer @arguments
