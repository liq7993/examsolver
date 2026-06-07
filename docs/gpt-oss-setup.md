# GPT-OSS 接入指南

> 怎么把本地 LLM 从 Gemma 4 切换到 GPT-OSS 20B。**面向 Windows + llama-server 用户**。

---

## TL;DR

```powershell
# 0. 拿到 GGUF（见 §1）
# 1. 切到 GPT-OSS preset 启栈
.\scripts\start-examsolver-with-gpt-oss.ps1
# 2. 想回 Gemma 就跑另一个脚本
.\scripts\start-examsolver-with-gemma.ps1
```

---

## §1 获取 GPT-OSS GGUF（推荐路径）

### 先决条件

你需要本机存有：
- **GPT-OSS 20B**：HuggingFace safetensors 原版（不能直接喂 llama-server）或已量化的 GGUF
- **Gemma 4**：作为默认 fallback 的 GGUF（路径由 `$env:EXAMSOLVER_GEMMA4_GGUF_PATH` 指向）

llama-server 需要 GGUF。三条路：

### 路径 A · 下载社区 GGUF（推荐，最快）

去 HuggingFace 下载已经量化好的 GGUF，10 分钟搞定：

- **首选**：[ggml-org/gpt-oss-20b-GGUF](https://huggingface.co/ggml-org/gpt-oss-20b-GGUF)（官方维护）
- 备选：`bartowski/gpt-oss-20b-GGUF`、`unsloth/gpt-oss-20b-GGUF`

下载这个文件：

```
gpt-oss-20b-Q4_K_M.gguf   (~12 GB)
```

放到本机任意位置，然后通过环境变量告诉脚本：

```powershell
$env:EXAMSOLVER_GPT_OSS_20B_PATH = "<your-models-dir>\gpt-oss-20b\gpt-oss-20b-Q4_K_M.gguf"
```

> [!tip] 显存预算
> - 8GB 显存：用 Q3_K_M（~9 GB），减一些上下文（`-ContextSize 8192`）
> - 16GB 显存：Q4_K_M（推荐）
> - 24GB+ 显存：Q5_K_M 或 Q6_K，质量更好

### 路径 B · 自己量化（你只下了 safetensors 时）

需要 llama.cpp 工具。**估时 30-60 分钟 + 模型 + 量化空间**。把 `<llama-cpp-dir>` 替换成你本机的 llama.cpp 克隆路径、`<gpt-oss-dir>` 替换成 safetensors 所在目录：

```powershell
# 1. 克隆 llama.cpp（如果还没）
git clone https://github.com/ggerganov/llama.cpp <llama-cpp-dir>
cd <llama-cpp-dir>
pip install -r requirements.txt

# 2. safetensors → fp16 GGUF
python convert_hf_to_gguf.py `
    <gpt-oss-dir> `
    --outfile <gpt-oss-dir>\gpt-oss-20b-f16.gguf `
    --outtype f16

# 3. 量化到 Q4_K_M（编译过的 llama-quantize.exe）
.\build\bin\llama-quantize.exe `
    <gpt-oss-dir>\gpt-oss-20b-f16.gguf `
    <gpt-oss-dir>\gpt-oss-20b-Q4_K_M.gguf `
    Q4_K_M

# 4. 删 fp16 中间产物（占空间）
Remove-Item <gpt-oss-dir>\gpt-oss-20b-f16.gguf
```

### 路径 C · Ollama 用户

```powershell
ollama pull gpt-oss:20b
# Ollama 模型存到 %USERPROFILE%\.ollama\models\...
# 设环境变量指向 Ollama 服务（端口 11434）：
$env:EXAMSOLVER_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:EXAMSOLVER_LLM_MODEL = "gpt-oss:20b"
```

不需要单独的 llama-server。但 JSON schema 强约束在 Ollama 上不如 llama-server 稳。

---

## §2 启动方式

### 一次性配置环境变量

启动脚本读这三个环境变量，建议加到你的 PowerShell `$PROFILE`：

```powershell
$env:EXAMSOLVER_LLAMA_SERVER       = "<absolute path to llama-server.exe>"
$env:EXAMSOLVER_GEMMA4_GGUF_PATH   = "<absolute path to gemma 4 GGUF>"
$env:EXAMSOLVER_GEMMA4_MMPROJ_PATH = "<absolute path to gemma 4 mmproj>"
$env:EXAMSOLVER_GPT_OSS_20B_PATH   = "<absolute path to gpt-oss-20b GGUF>"
```

未设置时也可以每次启动传参覆盖（见参数表）。

### 一键启栈

```powershell
.\scripts\start-examsolver-with-gpt-oss.ps1
```

参数（全部可选，默认值来自上面的环境变量）：

| 参数 | 默认源 | 说明 |
|---|---|---|
| `-LlamaServer` | `$env:EXAMSOLVER_LLAMA_SERVER` | llama-server.exe 路径 |
| `-ModelPath` | `$env:EXAMSOLVER_GPT_OSS_20B_PATH` | GGUF 路径 |
| `-LlmPort` | 8080 | llama-server 端口 |
| `-AppPort` | 8000 | Examsolver FastAPI 端口 |
| `-ContextSize` | 32768 | 上下文长度（最大 131072，但吃显存）|
| `-NoBrowser` | switch | 不自动开浏览器 |

### 只启 llama-server

```powershell
.\scripts\start-gpt-oss-local-llm.ps1
```

### 与 Gemma 共存

两个脚本互不干扰。同时只能跑一个（都监听 8080）。切换：杀掉旧的、跑新的。

---

## §3 环境变量速查

`config.py` 支持 preset 机制：

```powershell
# 切 GPT-OSS（preset 决定 model / model_path / timeout / max_tokens 默认）
$env:EXAMSOLVER_LLM_PRESET = "gpt-oss-20b"

# 任意 per-key 覆盖
$env:EXAMSOLVER_LLM_MODEL = "gpt-oss-20b-custom"
$env:EXAMSOLVER_LLM_MAX_TOKENS = "2048"
```

可选 preset：`gemma4`（默认）/ `gpt-oss-20b` / `gpt-oss-120b`。

---

## §4 GPT-OSS 特殊事项

### Harmony 聊天模板

GPT-OSS 用 OpenAI 自家 Harmony 模板（不是 chatml）。`start-gpt-oss-local-llm.ps1` 已经传了 `--jinja`，最新 llama.cpp 会从 GGUF metadata 自动用 Harmony。**无需手动配置**。

如果 llama-server 报 "no chat template"，传一个本地的 `chat_template.jinja`：

```powershell
.\scripts\start-gpt-oss-local-llm.ps1 -ChatTemplate "<path-to-chat_template.jinja>"
```

### Reasoning effort

GPT-OSS 支持 `reasoning_effort: "low" | "medium" | "high"`。当前 `local_gguf.py` 没暴露此参数（不影响功能，但高质量场景可能想用 high）。后续如有需要，加在 `LocalGGUFClient.chat()` kwargs。

### JSON 结构化输出

llama-server `response_format={"type":"json_schema","strict":true}` 兼容 GPT-OSS。M2-03 已经实现，无需改。

---

## §5 切换前快速验证

GGUF 到位 + 环境变量设好后，先跑一遍：

```powershell
# 1. 起 llama-server
.\scripts\start-gpt-oss-local-llm.ps1

# 2. 另开终端，curl 测一下
curl http://127.0.0.1:8080/v1/models
# 期望返回 {"object":"list","data":[{"id":"gpt-oss-20b",...}]}

curl http://127.0.0.1:8080/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{"model":"gpt-oss-20b","messages":[{"role":"user","content":"你好"}],"max_tokens":100}'

# 3. 全栈起来
.\scripts\start-examsolver-with-gpt-oss.ps1

# 4. 路由准确率回归（10 条样本，参 docs/m2-routing-eval.md）
uv run python scripts/smoke.py "汽车 ABS 起到什么作用？"
```

如果 10 条样本中 ≥ 8 条路由结果与 Gemma 一致，**切换成功**，可以更新简历 / 答辩话术里把"本地 LLM"从 Gemma 改成 GPT-OSS。

---

## §6 出问题怎么办

| 症状 | 处理 |
|---|---|
| GGUF 找不到 | 检查 `$env:EXAMSOLVER_GPT_OSS_20B_PATH` 或 `-ModelPath`，确认文件真存在 |
| `chat template not found` | 加 `-ChatTemplate "<path-to-chat_template.jinja>"` |
| 显存爆 | 减 `-ContextSize 8192`，或换 Q3_K_M |
| 中文质量差 | GPT-OSS 中文略弱于 Gemma 中文版；高质量场景走云端 Claude（router 自然路由）|
| JSON 输出不稳 | llama-server 用 `--grammar` 强约束 + 重试（M2-03 已加重试 1 次）|
| 路由准确率 < 80% | 回退 Gemma：`.\scripts\start-examsolver-with-gemma.ps1` |

---

## §7 决策追溯

- **为什么是 GPT-OSS 不是 Qwen / Llama**：见 ARCHITECTURE.md ADR-008（用户偏好）
- **为什么本地 LLM 留 fallback**：见 ARCHITECTURE.md ADR-002（视觉上云、文本可本地）

---

*文档版本：v1.1 · GGUF 到位后跑一遍 §5 验证，然后把 README 主示例换成 GPT-OSS 脚本。*
