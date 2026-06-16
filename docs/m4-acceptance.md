# M4 验收记录

日期：2026-06-08

## 自动验证

- 后端：`186 passed, 3 skipped`
- 前端：`pnpm run build` 成功
- Ruff：通过
- 改动后端文件 mypy：通过
- `POST /solve` 实测 `sin(x)` 返回完整 `note`，答案为 `cos(x)`
- `POST /solve/images` 实测 PNG 上传成功并保存到受控目录
- `GET /export/docx/{solve_id}` 返回合法 docx，可被 `python-docx` 重开
- docx 的 `word/document.xml` 含原生 OMML `m:oMath` 和分式 `m:f`

## 视觉验证

- [首页](./m4-home.png)
- [一页一题](./m4-note.png)
- [历史页](./m4-history.png)

## M4-08 最终状态

- M4-08 已完成。
- 导出 Word 验收文件：`C:\Users\32044\examsolver-m4-word-check.docx`
- Windows Word COM 打开该 docx 后返回 `OMaths=3`、`Paragraphs=13`，确认 Word 识别到原生公式对象。
- 完成后提交 `M4: frontend + note page + export`

## 追加验收（2026-06-16）

- 修复 FastAPI CORS：允许 `localhost` / `127.0.0.1` 任意本地 dev 端口，避免 3000 被占用后前端换端口时浏览器 fetch 被拦。
- Edge headless 打开 `http://127.0.0.1:3010/note/73c76730b9054a2c8f466751a251b4e2`，note 页成功渲染，KaTeX 公式可见。
- Edge headless `--print-to-pdf` 生成 `C:\Windows\Temp\examsolver-m4-note-print.pdf`：PDF 3 页，文本中无“返回 / 导出 docx / 打印”，说明工具栏已被 print CSS 隐藏。
- 自动验证：`pnpm run build`、M4 后端定向 pytest、ruff、mypy 均通过。
