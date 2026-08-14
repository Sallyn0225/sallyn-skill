---
name: openai-image
description: 通过 OpenAI 兼容 API（可自定义 base_url 和 api_key，支持 OpenAI 官方或任何第三方兼容服务）进行图片生成和图片编辑。当用户要求生成图片、画图、文生图、制作插画/海报/头像/图标/壁纸（image generation），或要求编辑、修改、改图、换背景、局部重绘现有图片（image editing / inpainting）时，使用本技能。Use when the user wants to generate images from text prompts (generate an image, draw, text-to-image, 生图/画图) or edit/modify existing images (edit this image, change the background, 改图/换背景), even when the user does not explicitly mention OpenAI or an API.
---

# OpenAI 兼容图像生成与编辑

用 OpenAI 兼容的 Images API 完成文生图（`/images/generations`）与图片编辑（`/images/edits`）。
本 skill 自带零依赖 Python 脚本（仅标准库），用户通过 `config.json` 自定义 base_url 与 api_key，
可对接 OpenAI 官方或任意 OpenAI 兼容的第三方图像服务（SiliconFlow、DeepInfra、OneAPI 网关等）。

## 工作流程

1. 检查配置：脚本目录 `scripts/` 的上一级（skill 根目录）是否存在 `config.json`。
   - 不存在 → 先执行 `python scripts/openai_image.py init` 生成，再按用户要求填入 `base_url` / `api_key` / `model`（用户未提供 key 时，先询问用户）。
   - 已存在 → 直接使用；不确定时运行 `python scripts/openai_image.py config` 查看（key 打码显示）。
2. 判断任务类型：
   - 无输入图片 → `generate` 子命令。
   - 有输入图片 → `edit` 子命令。
3. 构造提示词并执行脚本（见下方命令速查）。
4. 脚本把生成的图片保存到 `-o` 指定路径（默认 `image-<时间戳>.png`），并在 stdout 输出 JSON（含保存路径、usage、revised_prompt）。向用户报告保存的文件路径；用 markdown 内嵌图片或让用户打开文件查看结果。

## 命令速查

脚本路径：`<skill根目录>/scripts/openai_image.py`（下文用 `scripts/openai_image.py` 代指）。

```bash
# 初始化配置（把 config.example.json 复制为 config.json）
python scripts/openai_image.py init

# 查看当前配置（key 打码）
python scripts/openai_image.py config

# 文生图
python scripts/openai_image.py generate --prompt "一只戴贝雷帽的橘猫，水彩插画" -o cat.png

# 图片编辑（单图）
python scripts/openai_image.py edit --image photo.jpg --prompt "把背景换成星空" -o edited.png

# 图片编辑（多张参考图 + 遮罩）
python scripts/openai_image.py edit --image a.png --image b.png --mask mask.png \
  --prompt "保留 a 的主体，背景换成 b 的沙滩场景" -o out.png

# 常用参数
python scripts/openai_image.py generate --prompt "..." --size 1024x1536 --quality high \
  --n 2 --output-format jpeg -o ./out
```

提示词很长时用 `--prompt-file prompt.txt` 从 UTF-8 文本文件读取。

## 配置（config.json）

由 `config.example.json` 复制而来，位于 skill 根目录：

```json
{
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-xxxx",
  "model": "gpt-image-1"
}
```

- `base_url`：服务根地址。默认 OpenAI 官方；第三方服务填其兼容端点（通常以 `/v1` 结尾）。
- `api_key`：密钥。提醒用户：`config.json` 含密钥、不要提交到版本库（本目录通常在 .gitignore 中）。
- `model`：默认模型。可选 `gpt-image-1`（默认，生图+编辑）、`gpt-image-1-mini`（更快更便宜）、
  `dall-e-3`（高质量但仅 `n=1`）、`dall-e-2`（精确 mask 编辑）等，取决于目标服务支持的模型。
- 命令行 `--base-url` / `--api-key` / `--model` 可临时覆盖配置，适合多账号切换。

## 参数速查

生成与编辑共用的可选参数（生成走 JSON body，编辑走 multipart 表单，脚本自动处理）：

| 参数 | 取值 | 说明 |
|---|---|---|
| `--size` | `1024x1024`、`1024x1536`、`1536x1024`、`2048x2048`、`auto`… | gpt-image 系列；dall-e-3 用 `1792x1024`/`1024x1792`，dall-e-2 最大 `1024x1024` |
| `--quality` | `low` / `medium` / `high` / `auto` | 草稿→成品；`low` 快而便宜 |
| `--output-format` | `png` / `jpeg` / `webp` | 默认 png；jpeg 最快 |
| `--background` | `transparent` / `opaque` / `auto` | 透明背景（gpt-image-2 不支持 transparent） |
| `--moderation` | `auto` / `low` | 审核强度 |
| `--n` | 1–10 | 生成张数（dall-e-3 固定 1） |
| `--response-format` | `b64_json` / `url` | 仅 dall-e 系列；脚本对 dall-e 自动加 `b64_json` |

编辑专属：
- `--image PATH`（可多次）：输入图片。第一张为主图；提供 mask 时 mask 作用于第一张。
- `--mask PATH`：PNG 遮罩，必须带 alpha 通道、与主图同尺寸同格式（<50MB）。透明区域 = 待修改区域。
  gpt-image 的 mask 是提示词式引导，不保证像素级精确——局部修改务必在提示词里明确"改哪里、改成什么"。

完整参数与模型能力对照见 `references/api-reference.md`（需要精确约束时查阅）。

## 提示词建议

- 具体 > 抽象：描述主体、动作、环境、光线、构图、风格、色调、镜头（如 "广角/特写"）、媒介（如 "水彩/3D 渲染/胶片摄影"）。
- 局部编辑要明确："只改 X，保持其他部分完全不变"。
- dall-e-3 会输出 `revised_prompt`（模型改写后的提示词），结果不理想时可参考它以改进措辞。
- 生图请求最长可能近 2 分钟，脚本超时为 300 秒，勿自行中断。

## 错误处理

| 现象 | 处置 |
|---|---|
| 401 | key 错误 → 让用户检查 config.json |
| 404 | 端点/模型不存在 → 确认 base_url 是否正确、该服务是否实现 images 端点 |
| 403 | 模型无权限（gpt-image 系列可能需完成 Organization Verification）→ 换模型或告知用户 |
| 429 / 5xx | 脚本自动指数退避重试 3 次；仍失败 → 稍后再试 |
| `moderation_blocked` | 内容审核拦截 → 改写提示词，不要原样重试 |
| 第三方服务参数报错 | 该服务只支持参数子集 → 去掉多余参数（如 background/moderation）重试 |

## 注意事项

- 脚本 stdout 只输出结果 JSON（含 `saved` 文件路径数组）；过程日志在 stderr，解析时不要混淆。
- 多张图（`--n > 1`）时 `-o` 会被当作目录处理，文件名形如 `image-0.png`。
- 响应里若既有 `b64_json` 又有 `url`，脚本优先用 `b64_json` 落盘。
- 生成结束后，向用户明确给出文件路径，并视上下文在回答中展示图片。
