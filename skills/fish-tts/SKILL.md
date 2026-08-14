---
name: fish-tts
description: 使用 Fish Audio API 把文字转成语音（TTS）：朗读文本、生成配音/旁白、制作有声内容、把文章/台词/字幕/脚本转成 mp3/wav/pcm/opus 音频文件。当用户要求"文字转语音"、"语音合成"、"朗读这段话"、"把这段文字变成音频/MP3"、"配音"、"AI 语音"、"有声书"或任何需要把文本变成人声文件的需求时，都使用本技能——即使用户没有提到 Fish Audio 或 API。本技能自带零依赖 Python 脚本和 config.json，允许用户配置 API key、TTS 模型（s2.1-pro / s2.1-pro-free / s2-pro / s1）、默认音色（reference_id）以及格式、码率、语速、音量、延迟等全部常用参数。
---

# Fish Audio 文字转语音

用 Fish Audio 的 TTS API（`POST https://api.fish.audio/v1/tts`）把文本合成为自然语音。
本 skill 自带零依赖 Python 脚本（仅标准库），用户通过 `config.json` 配置 API key、默认模型、默认音色和音质参数；支持音色库搜索、零样本音色克隆与多说话人对话。

## 工作流程

1. 检查配置：skill 根目录（`scripts/` 的上一级）是否存在 `config.json`。
   - 不存在 → 执行 `python scripts/fish_tts.py init` 生成，然后请用户提供 API key（在 fish.audio 的 API Keys 页面创建）并填入；用户未提供 key 时先询问，不要凭空编造。
   - 已存在 → 直接使用；不确定内容时运行 `python scripts/fish_tts.py config` 查看（key 打码显示）。
2. 若用户没有指定音色（reference_id）：
   - 用 `python scripts/fish_tts.py voices --search <关键词>` 搜索音色库，把候选音色的 id/名称列给用户挑选；或询问用户是否有自己的克隆音色 id；把选定的 id 写进 config.json 的 `reference_id` 作为默认。
3. 确认文本与参数（格式、语速、音量等；中文配音注意语速和停顿），执行合成（见命令速查）。
4. 脚本把音频保存到 `-o` 指定路径（默认 `tts-<时间戳>.<格式>`），stdout 输出 JSON（含保存路径、模型、字节数）。向用户报告文件路径；可顺带用系统播放器打开，或告诉用户如何试听。

## 命令速查

脚本路径：`<skill根目录>/scripts/fish_tts.py`（下文以 `scripts/fish_tts.py` 代指）。

```bash
# 初始化配置（把 config.example.json 复制为 config.json）
python scripts/fish_tts.py init

# 查看当前配置（key 打码）
python scripts/fish_tts.py config

# 基础合成（用 config.json 里的 model + reference_id）
python scripts/fish_tts.py tts --text "你好，欢迎收听今天的节目。" -o hello.mp3

# 指定音色合成（voice id 用 voices 子命令查）
python scripts/fish_tts.py tts --text "..." --reference-id <voice-id> -o out.mp3

# 长文本（从文件读，UTF-8）
python scripts/fish_tts.py tts --text-file 台本.txt --speed 1.2 --volume 2 -o dub.mp3

# 搜索音色库
python scripts/fish_tts.py voices --search 女声
python scripts/fish_tts.py voices --language zh --page-size 20

# 零样本音色克隆（参考音频 + 逐字转录，10-30 秒干净样本效果最好）
python scripts/fish_tts.py tts --text "..." \
  --reference-audio sample.wav --reference-text "参考音频的逐字内容" -o clone.mp3

# 多说话人对话（S2 系列模型；--reference-id 传多次，文本用 speaker 标记）
python scripts/fish_tts.py tts --text "<|speaker:0|>你好！<|speaker:1|>你好呀！" \
  --reference-id <voice-a> --reference-id <voice-b> -o dialogue.mp3

# 高质量 WAV（无损）
python scripts/fish_tts.py tts --text "..." --format wav --sample-rate 44100 -o out.wav
```

长文本直接用 `--text-file`；不要手动分段——服务端按 `chunk_length` 自动切分并保持音色一致。

## 配置（config.json）

由 `config.example.json` 复制而来，位于 skill 根目录。所有字段都可按用户需求修改；`scripts/fish_tts.py config` 查看现状（key 打码）：

```json
{
  "base_url": "https://api.fish.audio",
  "api_key": "YOUR_FISH_AUDIO_API_KEY",
  "model": "s2.1-pro",
  "reference_id": "",
  "format": "mp3",
  "mp3_bitrate": 128,
  "sample_rate": 44100,
  "latency": "normal",
  "chunk_length": 300,
  "normalize": true,
  "speed": 1.0,
  "volume": 0,
  "normalize_loudness": true,
  "temperature": 0.7,
  "top_p": 0.7,
  "max_new_tokens": 1024,
  "repetition_penalty": 1.2,
  "min_chunk_length": 50,
  "condition_on_previous_chunks": true,
  "early_stop_threshold": 1.0,
  "features": []
}
```

- `api_key`：必填。在 fish.audio 后台（API Keys 页面）创建。提醒用户：config.json 含明文密钥，不要提交到版本库。
- `model`：`s2.1-pro`（推荐，生产质量）、`s2.1-pro-free`（免费测试档）、`s2-pro`（上一代，多说话人）、`s1`（支持 `(情绪)` 括号标签）。模型经请求头发送。
- `reference_id`：默认音色。留空则每次合成必须显式 `--reference-id`（或零样本克隆）。填上后 `tts` 子命令可省略音色参数。
- `format`：`mp3`（默认）/ `wav`（无损）/ `pcm`（裸采样）/ `opus`（流式高效）。
- `mp3_bitrate`：64/128/192；`sample_rate`：opus 用 48000，其他一般 44100。
- `latency`：`normal`（最稳）/ `balanced`（首音约 300ms）/ `low`（最快）。
- `chunk_length`：100–300（官方默认 300），越小首音越快，越大长文本更高效。
- `speed`（0.5–2.0）、`volume`（-20~20 dB，支持小数）、`normalize_loudness`（响度归一化，S2 系列生效）、`temperature`/`top_p`（0–1，表现力/多样性）。
- 高级采样参数（官方默认已调优，一般不动）：`max_new_tokens`（1024）、`repetition_penalty`（1.2，>1 减少复读）、`min_chunk_length`（50，0-100）、`condition_on_previous_chunks`（true，前文保持音色一致）、`early_stop_threshold`（1.0，0-1）、`features`（请求级特性开关数组，如 `["quality-guard"]`）。
- 命令行参数（`--model`、`--format`、`--speed` 等）可临时覆盖配置，适合单次特殊需求；`--api-key` / `--base-url` 可临时切换账号或网关。

## 参数速查

| 参数 | 取值 | 说明 |
|---|---|---|
| `--model` | s2.1-pro / s2.1-pro-free / s2-pro / s1 | 走请求头；s1 用 `(高兴)` 括号情绪标签 |
| `--reference-id` | 音色 id（可多次） | 传多次 = 多说话人，文本需 `<\|speaker:0\|>` 标记（仅 S2 系） |
| `--reference-audio` + `--reference-text` | 音频路径 + 转录文本 | 零样本克隆，需成对、数量一致 |
| `--format` | mp3 / wav / pcm / opus | 默认取 config（mp3） |
| `--mp3-bitrate` | 64 / 128 / 192 | 仅 mp3 |
| `--opus-bitrate` | -1000(自动)/24000/32000/48000/64000 | 仅 opus |
| `--sample-rate` | 如 44100 / 48000 | opus 必须 48000 |
| `--latency` | low / normal / balanced | 延迟与稳定性权衡 |
| `--chunk-length` | 100–300 | 分块大小 |
| `--speed` | 0.5–2.0 | 语速倍率 |
| `--volume` | -20 ~ 20（小数） | 音量（dB） |
| `--normalize-loudness` / `--no-normalize-loudness` | 开关 | 响度归一化（S2 系列，默认开） |
| `--temperature` / `--top-p` | 0–1 | 表现力 / 多样性 |
| `--max-new-tokens` | 整数 | 每分块最大音频 token（默认 1024） |
| `--repetition-penalty` | 数值 | 重复惩罚，>1 减少复读（默认 1.2） |
| `--min-chunk-length` | 0–100 | 切分新块最小字符数（默认 50） |
| `--condition-on-previous` / `--no-...` | 开关 | 前文音频保持音色一致（默认开） |
| `--early-stop-threshold` | 0–1 | 批处理早停阈值（默认 1） |
| `--features` | 逗号分隔 | 特性开关，如 `quality-guard` |
| `--normalize` / `--no-normalize` | 开关 | 中英文文本归一化（数字朗读更稳，默认开） |

完整字段表（含 `max_new_tokens`、`repetition_penalty`、`features` 等高级采样参数与多说话人细节）见 `references/api-reference.md`，需要精确调参或调试时查阅。

注意：opus 格式仅支持 48000Hz 采样率——脚本会自动把 44100 修正为 48000 并在 stderr 提示。

## 错误处理

| 现象 | 处置 |
|---|---|
| 401 | key 错误 → 让用户检查 config.json / 重新生成 key |
| 402 | 账户欠费/额度不足 → 提示用户到 fish.audio 查看或充值 |
| 404 | 端点或音色 id 不存在 → 用 `voices` 子命令确认 id，检查 base_url |
| 429 / 5xx | 脚本自动指数退避重试 3 次；仍失败 → 稍后再试 |
| 额度/credit 报错 | 账户余额不足 → 提示用户到 fish.audio 查看或充值 |
| opus 报采样率错 | 脚本已自动修正为 48000；仍报错请检查其它参数 |

## 注意事项

- 脚本 stdout 只输出结果 JSON（`saved` 为文件路径）；过程日志在 stderr，解析时不要混淆。
- 必须指定音色：config 无 `reference_id` 且命令行未传音色参数时，脚本会报错并提示（而不是用未知音色硬合成）。
- 中文长文本建议 `--normalize` 保持开启；英文缩写/单位朗读不对时再考虑关闭。
- 合成耗时随文本长度增长（可能 1–2 分钟+），脚本超时 300 秒，勿自行中断重试——429/5xx 已在脚本内自动退避重试。
- `s2.1-pro-free` 无 TTFA/DPA 保证，适合开发测试；正式交付用 `s2.1-pro`。
- 零样本克隆的参考音频要干净（无背景音乐/混响）、10–30 秒、转录逐字准确；反复复用同一音色时建议先在 fish.audio 克隆为音色模型，再复用其 reference_id。
- 多说话人合成仅 S2 系列支持；`s1` 模型请用 `(情绪)` 括号标签控制语气。
