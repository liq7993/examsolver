param(
  [string]$LlamaServer = "D:\ollma\llama-server.exe",
  [string]$ModelPath = "E:\AI\models\gpt-oss-20b\gpt-oss-20b-Q4_K_M.gguf",
  [int]$Port = 8080,
  [int]$ContextSize = 32768,
  [int]$GpuLayers = 999,
  [string]$ChatTemplate = ""
)

# Start GPT-OSS 20B locally via llama-server (OpenAI-compatible API).
# - GPT-OSS uses the Harmony chat template. Recent llama.cpp auto-detects it from
#   the GGUF metadata; we pass --jinja to be explicit.
# - Context default is 32k to balance VRAM and recall on a single 16-24GB GPU.
#   Raise to 131072 if you have headroom (the model supports up to 128k).
# - $ModelPath should point at the GGUF (not the safetensors original). See
#   docs/gpt-oss-setup.md for how to obtain or convert one.

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
  throw @"
GPT-OSS GGUF not found at: $ModelPath

Get a GGUF first (see docs/gpt-oss-setup.md):
  - Recommended: download ggml-org/gpt-oss-20b-GGUF from HuggingFace
  - Or convert E:\AI\models\gpt-oss-20b\ (safetensors) via llama.cpp's
    convert_hf_to_gguf.py + llama-quantize
"@
}

$arguments = @(
  "--model", $ModelPath,
  "--host", "127.0.0.1",
  "--port", [string]$Port,
  "--ctx-size", [string]$ContextSize,
  "--n-gpu-layers", [string]$GpuLayers,
  "--jinja"
)

if ($ChatTemplate -ne "" -and (Test-Path -LiteralPath $ChatTemplate)) {
  $arguments += @("--chat-template-file", $ChatTemplate)
}

Write-Host "Starting GPT-OSS 20B local LLM on http://127.0.0.1:$Port/v1"
Write-Host "Model: $ModelPath"
Write-Host "Context: $ContextSize tokens"
& $resolvedLlamaServer @arguments
