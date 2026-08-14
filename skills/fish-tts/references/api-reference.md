# Fish Audio TTS API 参考（精编自 docs.fish.audio）

> 来源：https://docs.fish.audio/features/text-to-speech 与
> https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech
> 需要精确约束或调试时查阅本文件；日常使用看 SKILL.md 即可。

## 目录

1. 认证与获取 API Key
2. 模型选择
3. `POST /v1/tts` 请求字段全表
4. 音色（reference_id / references / 多说话人）
5. 输出格式与码率
6. 高级采样参数（TTSConfig）
7. 错误处理
8. 相关端点（音色库、克隆、流式）

---

## 1. 认证与获取 API Key

- 注册/登录 fish.audio，在 API Keys 页面创建 key：
  - 新后台：https://fish.audio/app/api-keys
- 所有请求带 `Authorization: Bearer <API_KEY>` 头。
- key 是明文凭据：不要提交到 git、不要写进日志；config.json 应加入 .gitignore。

## 2. 模型选择

| 模型 | 说明 | 适用 |
|---|---|---|
| `s2.1-pro` | 当前推荐，质量/延迟/吞吐优于 s2-pro | 生产默认 |
| `s2.1-pro-free` | 同模型免费额度，无 TTFA/DPA 保证 | 测试、原型、小流量 |
| `s2-pro` | 上一代 S2，多说话人、自然语言表现力控制 | 兼容旧工作流 |
| `s1` | 更早一代，支持 `(括号)` 情绪标签 | 需要 `(高兴)` 式情绪控制 |

- 模型通过请求头 `model` 指定（不是 body）；省略或无法识别时回退 `s2.1-pro`。
- 多说话人对话合成仅 S2 系列（`s2-pro` / `s2.1-pro` / `s2.1-pro-free`）支持，`s1` 不支持。
- `s1` 情绪示例：`今天天气真不错(高兴)`；也可 `[愤怒]` 形式。

## 3. POST /v1/tts 请求字段全表

请求头：`Authorization: Bearer <key>`、`Content-Type: application/json`、`model: <模型>`。
成功响应：200 + 音频二进制（按 `format` 对应 mime）；失败：非 200 + JSON 错误。

| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `text` | string | 必填 | 要合成的文本 |
| `reference_id` | string / string[] | 无 | 音色模型 id；数组 = 多说话人（S2 系） |
| `references` | ReferenceAudio[] / 2D | 无 | 零样本克隆参考音频（单说话人一维数组；多说话人二维数组） |
| `temperature` | number 0–1 | 0.7 | 表现力，越高越多样 |
| `top_p` | number 0–1 | 0.7 | 核采样多样性 |
| `prosody` | {speed, volume, normalize_loudness} | null | `speed` 0.5–2.0；`volume` -20~20 dB；`normalize_loudness` 响度归一化（S2 系列生效，s1 接受但无效） |
| `chunk_length` | int 100–300 | 300 | 分块大小，越小首音越快 |
| `normalize` | boolean | true | 中英文文本归一化，数字更稳定 |
| `format` | enum | mp3 | `mp3` / `wav` / `pcm` / `opus` |
| `sample_rate` | int/null | null | null 时用格式默认（多数 44100，opus 48000） |
| `mp3_bitrate` | 64/128/192 | 128 | 仅 format=mp3 |
| `opus_bitrate` | -1000/24000/32000/48000/64000 | -1000 | 仅 format=opus；-1000=自动 |
| `latency` | low/normal/balanced | normal | normal 最稳；balanced 首音约 300ms；low 最快 |
| `max_new_tokens` | int | 1024 | 每 chunk 最大音频 token |
| `repetition_penalty` | number | 1.2 | >1 减少复读/卡顿 |
| `min_chunk_length` | int 0–100 | 50 | 切分新 chunk 的最小字符数 |
| `condition_on_previous_chunks` | bool | true | 用前文音频保持音色一致 |
| `early_stop_threshold` | number 0–1 | 1 | 批处理早停阈值 |
| `features` | string[] | 无 | 请求级特性开关，如 `["quality-guard"]` |

ReferenceAudio：`{ "audio": "<base64 音频字节>", "text": "<该音频的逐字转录>" }`。

## 4. 音色

- **音色模型 id（reference_id）**：在 Voice Library 找现成音色，或克隆后使用。id 是形如十六进制的字符串。
- **零样本克隆**：直接给 `references`（10–30s 干净样本 + 逐字转录），无需训练。要反复复用建议先克隆保存为音色模型。
- **多说话人（S2 系）**：
  - `reference_id` 传数组 `["id-a", "id-b"]`，文本中插入说话人标记：`<|speaker:0|>你好！<|speaker:1|>你好呀！`
  - 零样本多说话人：`references` 传二维数组（每个内层数组是一个说话人的样本集），`reference_id` 传任意标识符数组。
- 本 skill 的脚本：`--reference-id` 传多次即为多说话人数组；零样本克隆用 `--reference-audio` + `--reference-text` 配对传参。

## 5. 输出格式与码率

| 格式 | 说明 |
|---|---|
| `mp3`（默认） | 体积/质量均衡；`mp3_bitrate` 64/128/192 |
| `wav` | 无损最高质量；配 `sample_rate`（如 44100） |
| `pcm` | 裸采样无容器，低延迟播放/电话管线 |
| `opus` | 流式高效；码率自动（`opus_bitrate=-1000`） |

## 6. 高级采样参数（TTSConfig）

以下参数与官方 API 参考一致，默认值已调优，仅在需要确定性或压制伪影时调整。本 skill 的零依赖脚本已全部暴露（config.json 或对应 CLI 参数）：`max_new_tokens`（1024）、`repetition_penalty`（1.2）、`min_chunk_length`（50，0-100）、`condition_on_previous_chunks`（true）、`early_stop_threshold`（1.0，0-1）、`features`（如 `["quality-guard"]`）。

## 7. 错误处理

| 现象 | 处置 |
|---|---|
| 401 | key 错误 → 检查 config.json / 重新生成 key |
| 402 | 账户欠费/额度不足 → 检查 fish.audio 账户余额 |
| 404 | 端点或 reference_id 不存在 → `voices` 搜索确认 id |
| 429 / 5xx | 脚本自动指数退避重试 3 次；仍失败 → 稍后重试 |
| 额度/credit 相关报错 | 检查 fish.audio 账户余额 |
| opus + 采样率报错 | 脚本已自动修正为 48000 |

## 8. 相关端点

- `POST /v1/tts` — 本 skill 使用的同步合成端点（也支持 MessagePack body，SDK 场景）。
- `GET /model` — 音色库列表/搜索（脚本 `voices` 子命令；参数 page_size/page_number/title/tag/self/author_id/language/title_language/sort_by，sort_by 可选 score/task_count/created_at）。注意脚本 CLI 中 `--search` 对应 title，`--tag` 对应 tag，`--self-only` 对应 self=true。
- 语音克隆（`create` 音色模型）：上传 10–60s 干净音频 + 转录训练，返回可复用的 reference_id。本 skill 不内置训练脚本；需要时参考 https://docs.fish.audio/features/voice-cloning。
- 流式端点（websocket / stream with timestamps）：适合实时 LLM token 朗读、字幕时间戳等场景；本 skill 脚本不支持，需要时用官方 SDK（`pip install fish-audio-sdk`，`client.tts.stream_websocket(...)`）。
