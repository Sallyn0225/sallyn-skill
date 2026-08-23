# OpenAI 图像 API 参考（依据官方文档整理）

> 来源：OpenAI 官方 Images API Reference 与 Image generation guide。
> 最近更新：2026-08-20 透明背景 preview（gpt-image-2 / gpt-image-2-2026-04-21）；2026-04-21 发布 gpt-image-2。
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
| `model` | string，必填 | 如 `gpt-image-1`、`gpt-image-1-mini`、`gpt-image-1.5`、`gpt-image-2`、`gpt-image-2-2026-04-21`、`dall-e-2`、`dall-e-3` |
| `prompt` | string，必填 | 文字提示词 |
| `n` | int | 生成张数，默认 1。dall-e-3 只支持 1；dall-e-2 最多 10；gpt-image 系列 1–10 |
| `size` | string | 见第 6 节。默认 1024x1024；gpt-image 系列支持 `auto` |
| `quality` | string | `low` / `medium` / `high` / `auto`（gpt-image 系列）。dall-e-3 仅 `standard`/`hd`（部分兼容服务忽略） |
| `output_format` | string | `png`（默认）/ `webp` / `jpeg`（gpt-image 系列） |
| `output_compression` | int | 0–100，仅 jpeg/webp 生效（gpt-image 系列） |
| `background` | string | `transparent` / `opaque` / `auto`（gpt-image 系列）。**透明背景：gpt-image-2 及 gpt-image-2-2026-04-21 为 preview（2026-08-20 起）**，gpt-image-1/1.5/1-mini 亦支持；必须搭配 `png`/`webp` 输出，`jpeg` 不支持透明。提示词优先级高于本参数（详见第 6 节） |
| `moderation` | string | `auto`（默认）/ `low`（gpt-image 系列） |
| `response_format` | string | 仅 dall-e-2/dall-e-3：`url`（默认）/ `b64_json`。gpt-image 系列恒返回 b64_json |
| `partial_images` | int | 0–3，流式返回中间图（本脚本未实现，见第 9 节） |

注意：`output_format`、`quality`、`background`、`moderation` 是 gpt-image 系列的参数；
对 dall-e-2/dall-e-3 应使用 `response_format` 而不是 `output_format`。
第三方兼容服务可能只支持参数子集，多余的参数可能被忽略或报错——报错时去掉多余参数重试。

提示词长度：GPT image 系列最长 32,000 字符，dall-e-3 为 4,000，dall-e-2 为 1,000。

## 3. POST /images/edits 参数

multipart/form-data body（脚本已自动构造）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `model` | string，必填 | 同上 |
| `prompt` | string，必填 | 描述期望的修改结果 |
| `image[]` | file，必填 | 输入图片，可多张（最多 16 张）。第一张为主图；提供 mask 时 mask 应用于第一张 |
| `mask` | file，可选 | PNG 遮罩，需带 alpha 通道，透明区域 = 待修改区域 |
| 其余 | — | `n`、`size`、`quality`、`output_format`、`output_compression`、`background`、`moderation`、`response_format`、`stream` 与 generations 相同 |

GPT Image 的 mask 是「提示词式」遮罩：模型把 mask 当参考，不一定精确贴合形状。
想要精确局部修改时，提示词要明确说明要改哪里、改成什么。

编辑请求也可用 JSON body（见第 7 节）：`images` 数组 + `mask`，每项传 `file_id` 或 `image_url`。

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

| 模型 | 文生图 | 图片编辑 | 透明背景 | 备注 |
|---|---|---|---|---|
| gpt-image-2 / gpt-image-2-2026-04-21 | ✅ | ✅ | ✅（preview） | 最新旗舰；任意分辨率、自动高保真输入；token 计价；支持 Batch API（-50%） |
| gpt-image-1.5 / gpt-image-1 / gpt-image-1-mini | ✅ | ✅ | ✅ | 返回 b64_json；支持 quality/size/format/background/moderation |
| dall-e-3 | ✅ | ✅（仅生成式整图替换，不支持 mask） | ❌ | 返回 URL（默认）或 b64_json；`n` 固定 1；有 revised_prompt |
| dall-e-2 | ✅ | ✅ | ❌ | 支持 mask 精确编辑；分辨率低（最大 1024x1024） |

## 6. 尺寸 / 质量 / 格式约束

**gpt-image 系列常用尺寸**：`1024x1024`、`1536x1024`（横）、`1024x1536`（竖）、
`2048x2048`、`2048x1152`、`3840x2160`、`2160x3840`、`auto`。

gpt-image-2 支持任意分辨率，约束：最长边 ≤ 3840px；两边均为 16 的倍数；
长宽比 ≤ 3:1；总像素 655,360 – 8,294,400。

**dall-e-3**：`1024x1024`、`1792x1024`、`1024x1792`。
**dall-e-2**：`256x256`、`512x512`、`1024x1024`。

质量：`low`（草稿/缩略图，最快最便宜）→ `medium` → `high`（成品）。支持 `auto` 的模型会按提示词自动选择。
格式：`jpeg` 生成最快（对延迟敏感优先）；`png` 默认。

### 透明背景（background=transparent）

- 支持模型：gpt-image 系列；gpt-image-2 及 gpt-image-2-2026-04-21 为 preview（2026-08-20 起）。
- 输出格式必须是 `png`（默认）或 `webp`；**`jpeg` 不支持透明**。使用 PNG 时建议省略 `output_compression`。
- **提示词优先级高于 background 参数**：明确要求"主体独立、完全透明背景（isolated subject on a fully
transparent background）"，并避免描述场景、纯色背景、棋盘格、阴影等内容，否则模型可能生成不透明背景。
- 编辑场景：可重复强调"保留透明背景（preserve the transparent background）"，防止后续步骤补上新背景。
- 用途：贴纸、图标、商品图、演示文稿/海报素材等需要保留 alpha 通道做后期叠加的场景。
- 注意 preview 功能可能变化；部分社区反馈生成的 alpha 值约为 252–254 而非 255，下游如需纯透明可自行归一化。

## 7. Mask 要求

- 主图与 mask 尺寸、格式必须一致，且 < 50MB。
- mask 必须含 alpha 通道（RGBA PNG）。普通黑白图需程序化转换：
  将灰度图 `convert("RGBA")` 后用原图自身填充 alpha（Pillow 示例见官方文档）。
- 透明区域 = 待修改区域。
- gpt-image 系列的 mask 为提示词式引导，不保证像素级精确。
- 多张输入图时 mask 作用于第一张。

编辑请求除了脚本所用的 multipart 表单（`image[]` 字段）外，官方文档还提供 JSON body 方式：
`images` 数组内每项传 `{ "file_id": ... }`（Files API）或 `{ "image_url": ... }`（URL/base64 data URI），
mask 同样支持 `{ file_id }` / `{ image_url }` 引用。两种方式均可，脚本默认用 multipart。

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

官方支持 `stream: true` + `partial_images`（0–3），SSE 返回 `image_generation.partial_image` 事件；
`partial_images=0` 时只收最终图。每个 partial 额外计 100 输出 token。
本脚本为同步实现、不流式；需要逐帧预览的场景可后续扩展。
