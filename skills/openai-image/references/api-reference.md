# OpenAI 图像 API 参考（依据官方文档整理）

> 来源：OpenAI 官方 Images API Reference 与 Image generation guide。
> 本文档供需要精确参数信息时查阅；常规任务直接按 SKILL.md 的命令速查操作即可。

## 目录

1. 端点总览
2. POST /images/generations 请求参数
3. POST /images/edits 请求参数
4. 响应结构
5. 模型与能力对照
6. 尺寸 / 质量 / 格式约束
7. Mask（遮罩）要求
8. 错误处理
9. 流式（partial_images，脚本未实现）

---

## 1. 端点总览

| 端点 | 方法 | 用途 |
|---|---|---|
| `{base_url}/images/generations` | POST | 根据文字提示从零生成图片 |
| `{base_url}/images/edits` | POST | 编辑已有图片（改局部/整体、多图参考） |

`base_url` 默认 `https://api.openai.com/v1`，第三方 OpenAI 兼容服务可自定义。

## 2. POST /images/generations 参数

JSON body：

| 参数 | 类型 | 说明 |
|---|---|---|
| `model` | string，必填 | 如 `gpt-image-1`、`gpt-image-1-mini`、`gpt-image-1.5`、`gpt-image-2`、`dall-e-2`、`dall-e-3` |
| `prompt` | string，必填 | 文字提示词 |
| `n` | int | 生成张数，默认 1。dall-e-3 只支持 1；dall-e-2 最多 10；gpt-image 系列 1–10 |
| `size` | string | 见第 6 节。默认 1024x1024；gpt-image 系列支持 `auto` |
| `quality` | string | `low` / `medium` / `high` / `auto`（gpt-image 系列）。dall-e-3 仅 `standard`/`hd`（部分兼容服务忽略） |
| `output_format` | string | `png`（默认）/ `webp` / `jpeg`（gpt-image 系列） |
| `output_compression` | int | 0–100，仅 jpeg/webp 生效（gpt-image 系列） |
| `background` | string | `transparent` / `opaque` / `auto`（gpt-image 系列）。注意：`gpt-image-2` 不支持 `transparent` |
| `moderation` | string | `auto`（默认）/ `low`（gpt-image 系列） |
| `response_format` | string | 仅 dall-e-2/dall-e-3：`url`（默认）/ `b64_json`。gpt-image 系列恒返回 b64_json |
| `partial_images` | int | 0–3，流式返回中间图（本脚本未实现，见第 9 节） |

注意：`output_format`、`quality`、`background`、`moderation` 是 gpt-image 系列的参数；
对 dall-e-2/dall-e-3 应使用 `response_format` 而不是 `output_format`。
第三方兼容服务可能只支持参数子集，多余的参数可能被忽略或报错——报错时去掉多余参数重试。

## 3. POST /images/edits 参数

multipart/form-data body（脚本已自动构造）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `model` | string，必填 | 同上 |
| `prompt` | string，必填 | 描述期望的修改结果 |
| `image[]` | file，必填 | 输入图片，可多张。第一张为主图；提供 mask 时 mask 应用于第一张 |
| `mask` | file，可选 | PNG 遮罩，需带 alpha 通道，透明区域 = 待修改区域 |
| 其余 | — | `n`、`size`、`quality`、`output_format`、`output_compression`、`background`、`moderation`、`response_format` 与 generations 相同 |

GPT Image 的 mask 是「提示词式」遮罩：模型把 mask 当参考，不一定精确贴合形状。
想要精确局部修改时，提示词要明确说明要改哪里、改成什么。

## 4. 响应结构

```json
{
  "created": 1710000000,
  "data": [
    {
      "b64_json": "...",          // gpt-image 系列默认返回；dall-e 需 response_format=b64_json
      "url": "...",               // dall-e 默认返回临时 URL（约 1 小时有效）
      "revised_prompt": "..."     // 仅 dall-e-3：模型改写后的提示词
    }
  ],
  "output_format": "png",
  "quality": "medium",
  "size": "1024x1024",
  "usage": {                       // 仅 gpt-image 系列
    "input_tokens": 12,
    "input_tokens_details": {"text_tokens": 12, "image_tokens": 0},
    "output_tokens": 1056,
    "total_tokens": 1068
  }
}
```

## 5. 模型与能力对照

| 模型 | 文生图 | 图片编辑 | 备注 |
|---|---|---|---|
| gpt-image-1 / gpt-image-1-mini / gpt-image-1.5 / gpt-image-2 | ✅ | ✅ | 返回 b64_json；支持 quality/size/format/background/moderation |
| dall-e-3 | ✅ | ✅（仅生成式整图替换，不支持 mask） | 返回 URL（默认）或 b64_json；`n` 固定 1；有 revised_prompt |
| dall-e-2 | ✅ | ✅ | 支持 mask 精确编辑；分辨率低（最大 1024x1024） |

## 6. 尺寸 / 质量 / 格式约束

**gpt-image 系列常用尺寸**：`1024x1024`、`1536x1024`（横）、`1024x1536`（竖）、
`2048x2048`、`2048x1152`、`3840x2160`、`2160x3840`、`auto`。

gpt-image-2 支持任意分辨率，约束：最长边 ≤ 3840px；两边均为 16 的倍数；
长宽比 ≤ 3:1；总像素 655,360 – 8,294,400。

**dall-e-3**：`1024x1024`、`1792x1024`、`1024x1792`。
**dall-e-2**：`256x256`、`512x512`、`1024x1024`。

质量：`low`（草稿/缩略图，最快最便宜）→ `medium` → `high`（成品）。支持 `auto` 的模型会按提示词自动选择。
格式：`jpeg` 生成最快（对延迟敏感优先）；`png` 默认。

## 7. Mask 要求

- 主图与 mask 尺寸、格式必须一致，且 < 50MB。
- mask 必须含 alpha 通道（RGBA PNG）。普通黑白图需程序化转换：
  将灰度图 `convert("RGBA")` 后用原图自身填充 alpha（Pillow 示例见官方文档）。
- gpt-image 系列的 mask 为提示词式引导，不保证像素级精确。

## 8. 错误处理

| 情况 | 处理 |
|---|---|
| 401 | key 错误/未授权 → 检查配置 |
| 403 | 模型无权限；gpt-image 系列可能需完成 API Organization Verification |
| 404 | 端点或模型不存在 → 检查 base_url 与该服务是否实现 images 端点 |
| 429 / 5xx | 限流或服务端故障 → 脚本已内置指数退避重试（3 次）；仍失败则稍后再试 |
| `error.code = "moderation_blocked"` | 内容审核拦截，改写提示词，不要原样重试 |
| `error.type = "image_generation_user_error"` | 用户可修正错误（提示词/输入图问题），先改请求再重试 |

## 9. 流式（未实现）

官方支持 `partial_images`（0–3）+ SSE 返回 `image_generation.partial_image` 事件。
本脚本为同步实现、不流式；需要逐帧预览的场景可后续扩展。
