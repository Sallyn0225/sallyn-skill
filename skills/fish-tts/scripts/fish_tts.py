#!/usr/bin/env python3
"""
Fish Audio 文字转语音命令行工具（零第三方依赖，仅用 Python 标准库）。

端点：
  POST {base_url}/v1/tts        文字转语音（model 走请求头，其余参数走 JSON body）
  GET  {base_url}/model         列出/搜索音色（voice library）

配置：优先读取 skill 根目录下的 config.json（由 config.example.json 复制而来），
      命令行 --base-url / --api-key / --model 等参数可临时覆盖。

用法示例：
  python fish_tts.py tts --text "你好，世界" -o hello.mp3
  python fish_tts.py tts --text-file script.txt --reference-id <voice-id> --speed 1.2
  python fish_tts.py voices --search 女声
  python fish_tts.py init          # 生成 config.json
  python fish_tts.py config        # 查看当前配置（key 打码）
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://api.fish.audio"
DEFAULT_MODEL = "s2.1-pro"
DEFAULT_TIMEOUT = 300  # 长文本合成耗时较长，勿自行中断
MAX_RETRIES = 3

# Windows 下强制 UTF-8 输出，避免控制台 GBK 编码导致中文/JSON 乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_CONFIG_PATH = os.path.join(SKILL_ROOT, "config.json")

MODELS = ["s2.1-pro", "s2.1-pro-free", "s2-pro", "s1"]
FORMATS = ["mp3", "wav", "pcm", "opus"]
LATENCIES = ["low", "normal", "balanced"]


def eprint(*args):
    print(*args, file=sys.stderr)


class ApiError(Exception):
    """带 HTTP 状态码的接口错误。"""

    def __init__(self, status, message, body=None):
        super().__init__(message)
        self.status = status
        self.body = body or {}


# ---------------------------------------------------------------- 配置

def load_config(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        raise SystemExit(f"配置文件 {path} 解析失败：{exc}")


PLACEHOLDER_KEY = "YOUR_FISH_AUDIO_API_KEY"


def require_api_key(api_key, config_path):
    if not api_key or api_key == PLACEHOLDER_KEY or "YOUR_" in api_key:
        raise SystemExit(
            "API key 未配置。请编辑 config.json 填入你在 fish.audio 创建的 api_key，"
            f"或用 --api-key 传入。（配置文件位置：{config_path}）"
        )


def mask_key(key):
    if not key:
        return "(未设置)"
    return key[:6] + "..." + key[-4:] if len(key) > 12 else "***"


def first_defined(cli_value, cfg, key, default=None):
    """CLI 优先，其次 config.json，最后默认值。"""
    if cli_value is not None:
        return cli_value
    if key in cfg and cfg[key] is not None:
        return cfg[key]
    return default


# ---------------------------------------------------------------- HTTP

def http_request(url, headers, body=None, method="POST", timeout=DEFAULT_TIMEOUT):
    """带重试的 HTTP 请求。429/5xx 与网络错误自动退避重试。"""
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
            if status == 429 or status >= 500:
                last_error = (status, exc.headers, raw)
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    eprint(f"[retry] HTTP {status}，{wait}s 后重试（{attempt + 1}/{MAX_RETRIES}）…")
                    time.sleep(wait)
                    continue
            return status, exc.headers, raw
        except Exception as exc:
            last_error = (0, {}, str(exc).encode())
            if attempt < MAX_RETRIES:
                eprint(f"[retry] 网络错误：{exc}（{attempt + 1}/{MAX_RETRIES}）…")
                time.sleep(2 ** attempt)
                continue
            break
    status, headers, raw = last_error
    raise SystemExit(f"请求失败（HTTP {status}）：{raw.decode('utf-8', errors='replace')[:500]}")


def error_message(status, raw):
    """从错误响应 body 中提取可读的错误信息。"""
    try:
        data = json.loads(raw.decode("utf-8"))
    except ValueError:
        return raw.decode("utf-8", errors="replace")[:500] or f"HTTP {status}"
    if isinstance(data, dict):
        err = data.get("error") or {}
        if isinstance(err, dict):
            return err.get("message") or json.dumps(err, ensure_ascii=False)
        return data.get("message") or json.dumps(data, ensure_ascii=False)
    return str(data)


def error_hint(status, message):
    msg = (message or "").lower()
    if status == 401:
        return "API key 无效或未授权。请检查 config.json 中的 api_key，或在 fish.audio 后台重新生成。"
    if status == 404:
        return "端点或音色不存在。请确认 base_url 正确、reference_id 有效（用 voices 子命令搜索）。"
    if status == 429:
        return "限流或额度不足，稍后重试或检查账户余额/套餐。"
    if "credit" in msg or "quota" in msg or "balance" in msg:
        return "账户额度/余额不足，请到 fish.audio 后台查看或充值。"
    return "详见上方响应信息。"


# ---------------------------------------------------------------- TTS

def collect_text(args):
    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return args.text


def build_tts_body(args, cfg):
    """按 CLI > config.json 的优先级构造 TTS 请求体；未设置的字段不发送。"""
    body = {"text": collect_text(args)}

    # 音色：--reference-id 可多次传入（多说话人时转为数组）
    if args.reference_id:
        ref = args.reference_id if len(args.reference_id) > 1 else args.reference_id[0]
    else:
        ref = cfg.get("reference_id") or None
    if ref:
        body["reference_id"] = ref

    # 零样本音色克隆：--reference-audio 与 --reference-text 一一配对
    if args.reference_audio:
        if len(args.reference_audio) != len(args.reference_text or []):
            raise SystemExit(
                "reference-audio 与 reference-text 数量必须一致（每条音频配一条转录文本）。"
            )
        refs = []
        for audio_path, text in zip(args.reference_audio, args.reference_text):
            if not os.path.isfile(audio_path):
                raise SystemExit(f"参考音频不存在：{audio_path}")
            with open(audio_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode()
            refs.append({"audio": audio_b64, "text": text})
            eprint(f"[info] 参考音频 {audio_path}（{len(audio_b64) // 3 * 2 // 1024} KB）")
        body["references"] = refs

    if not body.get("reference_id") and not body.get("references"):
        raise SystemExit(
            "未指定音色。请用 --reference-id 指定 voice model id（用 voices 子命令搜索），"
            "或使用 --reference-audio + --reference-text 进行零样本克隆，"
            "或在 config.json 中配置默认 reference_id。"
        )

    fmt = first_defined(args.format, cfg, "format", "mp3")
    if fmt not in FORMATS:
        raise SystemExit(f"format 必须是 {FORMATS} 之一，收到：{fmt}")
    body["format"] = fmt

    if fmt == "mp3":
        mp3_bitrate = first_defined(args.mp3_bitrate, cfg, "mp3_bitrate", 128)
        if mp3_bitrate not in (64, 128, 192):
            raise SystemExit(f"mp3_bitrate 只能是 64/128/192，收到：{mp3_bitrate}")
        body["mp3_bitrate"] = mp3_bitrate
    if fmt == "opus":
        opus_bitrate = first_defined(args.opus_bitrate, cfg, "opus_bitrate", -1000)
        if opus_bitrate not in (-1000, 24000, 32000, 48000, 64000):
            raise SystemExit(f"opus_bitrate 只能是 -1000/24000/32000/48000/64000，收到：{opus_bitrate}")
        body["opus_bitrate"] = opus_bitrate

    sample_rate = first_defined(args.sample_rate, cfg, "sample_rate", None)
    if sample_rate is not None:
        sample_rate = int(sample_rate)
        if fmt == "opus" and sample_rate != 48000:
            # 规范：sample_rate 为 null 时 opus 默认 48000；配置里常驻 44100，自动修正避免冲突
            eprint(f"[warn] opus 格式已将 sample_rate {sample_rate} 自动修正为 48000（opus 仅支持 48kHz）")
            sample_rate = 48000
        body["sample_rate"] = sample_rate

    latency = first_defined(args.latency, cfg, "latency", "normal")
    if latency not in LATENCIES:
        raise SystemExit(f"latency 必须是 {LATENCIES} 之一，收到：{latency}")
    body["latency"] = latency

    chunk_length = first_defined(args.chunk_length, cfg, "chunk_length", None)
    if chunk_length is not None:
        chunk_length = int(chunk_length)
        if not 100 <= chunk_length <= 300:
            raise SystemExit(f"chunk_length 需在 100-300 之间，收到：{chunk_length}")
        body["chunk_length"] = chunk_length

    normalize = args.normalize if args.normalize is not None else cfg.get("normalize", True)
    body["normalize"] = bool(normalize)

    speed = first_defined(args.speed, cfg, "speed", None)
    volume = first_defined(args.volume, cfg, "volume", None)
    normalize_loudness = first_defined(args.normalize_loudness, cfg, "normalize_loudness", None)
    if speed is not None or volume is not None or normalize_loudness is not None:
        speed = float(speed) if speed is not None else 1.0
        volume = float(volume) if volume is not None else 0.0
        if not 0.5 <= speed <= 2.0:
            raise SystemExit(f"speed 需在 0.5-2.0 之间，收到：{speed}")
        if not -20 <= volume <= 20:
            raise SystemExit(f"volume 需在 -20 到 20 之间（dB），收到：{volume}")
        prosody = {"speed": speed, "volume": volume}
        if normalize_loudness is not None:
            # 响度归一化：S2 系列生效，s1 接受但无效果
            prosody["normalize_loudness"] = bool(normalize_loudness)
        body["prosody"] = prosody

    temperature = first_defined(args.temperature, cfg, "temperature", None)
    if temperature is not None:
        temperature = float(temperature)
        if not 0 <= temperature <= 1:
            raise SystemExit(f"temperature 需在 0-1 之间，收到：{temperature}")
        body["temperature"] = temperature

    top_p = first_defined(args.top_p, cfg, "top_p", None)
    if top_p is not None:
        top_p = float(top_p)
        if not 0 <= top_p <= 1:
            raise SystemExit(f"top_p 需在 0-1 之间，收到：{top_p}")
        body["top_p"] = top_p

    # ---- 高级采样参数（与官方 API 参考一致，默认值已调优，一般无需改动） ----
    max_new_tokens = first_defined(args.max_new_tokens, cfg, "max_new_tokens", None)
    if max_new_tokens is not None:
        body["max_new_tokens"] = int(max_new_tokens)

    repetition_penalty = first_defined(args.repetition_penalty, cfg, "repetition_penalty", None)
    if repetition_penalty is not None:
        body["repetition_penalty"] = float(repetition_penalty)

    min_chunk_length = first_defined(args.min_chunk_length, cfg, "min_chunk_length", None)
    if min_chunk_length is not None:
        min_chunk_length = int(min_chunk_length)
        if not 0 <= min_chunk_length <= 100:
            raise SystemExit(f"min_chunk_length 需在 0-100 之间，收到：{min_chunk_length}")
        body["min_chunk_length"] = min_chunk_length

    if args.condition_on_previous is not None:
        body["condition_on_previous_chunks"] = args.condition_on_previous
    elif "condition_on_previous_chunks" in cfg:
        body["condition_on_previous_chunks"] = bool(cfg["condition_on_previous_chunks"])

    early_stop_threshold = first_defined(args.early_stop_threshold, cfg, "early_stop_threshold", None)
    if early_stop_threshold is not None:
        early_stop_threshold = float(early_stop_threshold)
        if not 0 <= early_stop_threshold <= 1:
            raise SystemExit(f"early_stop_threshold 需在 0-1 之间，收到：{early_stop_threshold}")
        body["early_stop_threshold"] = early_stop_threshold

    features = args.features if args.features is not None else cfg.get("features")
    if features:
        body["features"] = [f.strip() for f in features] if isinstance(features, list) else \
                            [f.strip() for f in str(features).split(",") if f.strip()]

    return body


def cmd_tts(args):
    cfg = load_config(args.config)
    base_url = (args.base_url or cfg.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
    api_key = args.api_key or cfg.get("api_key") or ""
    model = args.model or cfg.get("model") or DEFAULT_MODEL
    require_api_key(api_key, args.config)
    if model not in MODELS:
        eprint(f"[warn] model={model} 不在已知列表 {MODELS}，若拼写错误将回退到 s2.1-pro。")

    body = build_tts_body(args, cfg)
    text_len = len(body["text"])

    eprint(f"[info] POST {base_url}/v1/tts  model={model}  format={body.get('format')}  "
           f"text={text_len} 字符")
    status, _, raw = http_request(
        f"{base_url}/v1/tts",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "model": model,
        },
        body=json.dumps(body, ensure_ascii=False).encode(),
    )

    if status >= 400:
        message = error_message(status, raw)
        raise ApiError(status, f"{message}\n提示：{error_hint(status, message)}", {})

    fmt = body.get("format", "mp3")
    out = args.output or f"tts-{int(time.time())}.{fmt}"
    with open(out, "wb") as f:
        f.write(raw)
    eprint(f"[saved] {out}（{len(raw)} bytes）")
    print(json.dumps({
        "saved": out,
        "model": model,
        "format": fmt,
        "bytes": len(raw),
        "text_chars": text_len,
    }, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- Voices

def cmd_voices(args):
    cfg = load_config(args.config)
    base_url = (args.base_url or cfg.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
    api_key = args.api_key or cfg.get("api_key") or ""
    require_api_key(api_key, args.config)

    params = {}
    for key in ("page_size", "page_number", "title", "tag", "author_id",
                "language", "title_language", "sort_by"):
        value = getattr(args, key, None)
        if value is not None:
            params[key] = value
    if args.self_only:
        params["self"] = True
    query = urllib.parse.urlencode(params)
    url = f"{base_url}/model" + (f"?{query}" if query else "")

    eprint(f"[info] GET {url}")
    status, _, raw = http_request(url, headers={"Authorization": f"Bearer {api_key}"},
                                  method="GET")

    if status >= 400:
        message = error_message(status, raw)
        raise ApiError(status, f"{message}\n提示：{error_hint(status, message)}", {})

    try:
        data = json.loads(raw.decode("utf-8"))
    except ValueError:
        raise SystemExit(f"voices 返回了非 JSON 内容：{raw.decode('utf-8', errors='replace')[:300]}")

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    items = data.get("items") or []
    total = data.get("total", len(items))
    eprint(f"[info] 共 {total} 个音色（本页 {len(items)} 个）")
    if not items:
        print("(无结果)")
        return
    # 对齐输出：id / title / visibility / tags
    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        vid = it.get("_id") or it.get("id") or it.get("voice_id") or "?"
        title = (it.get("title") or "").strip()
        visibility = it.get("visibility") or ""
        langs = it.get("languages") or it.get("language") or ""
        langs_s = ",".join(langs) if isinstance(langs, list) else str(langs)
        tags = it.get("tags") or []
        tags_s = ",".join(tags) if isinstance(tags, list) else str(tags)
        rows.append((vid, title, visibility, langs_s, tags_s))
    w_id = max(len(r[0]) for r in rows)
    w_title = max(len(r[1]) for r in rows)
    print(f"{'ID'.ljust(w_id)}  {'TITLE'.ljust(w_title)}  {'VISIBILITY':10}  {'LANGS':12}  TAGS")
    for vid, title, visibility, langs_s, tags_s in rows:
        print(f"{vid.ljust(w_id)}  {title.ljust(w_title)}  {visibility:10}  {langs_s:12}  {tags_s}")


# ---------------------------------------------------------------- init / config

def cmd_config(args):
    cfg = load_config(args.config)
    print(json.dumps({
        "config_path": args.config,
        "exists": os.path.isfile(args.config),
        "base_url": cfg.get("base_url") or DEFAULT_BASE_URL,
        "model": cfg.get("model") or DEFAULT_MODEL,
        "reference_id": cfg.get("reference_id") or "(未设置)",
        "format": cfg.get("format") or "mp3",
        "api_key": mask_key(cfg.get("api_key") or ""),
    }, ensure_ascii=False, indent=2))


def cmd_init(args):
    example = os.path.join(SKILL_ROOT, "config.example.json")
    if os.path.isfile(args.config) and not args.force:
        raise SystemExit(f"{args.config} 已存在。如需覆盖请加 --force。")
    if not os.path.isfile(example):
        raise SystemExit(f"找不到模板 {example}")
    with open(example, "r", encoding="utf-8") as f:
        content = f.read()
    with open(args.config, "w", encoding="utf-8") as f:
        f.write(content)
    print(json.dumps({"created": args.config}, ensure_ascii=False, indent=2))
    eprint(f"[info] 已创建 {args.config}，请填入 api_key；"
           "如需固定音色，把 voice model id 填到 reference_id。")


# ---------------------------------------------------------------- 参数解析

def common_args(parser):
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH,
                        help="配置文件路径（默认：skill 目录下的 config.json）")
    parser.add_argument("--base-url", help="覆盖配置中的 base_url")
    parser.add_argument("--api-key", help="覆盖配置中的 api_key")
    parser.add_argument("--model", choices=MODELS,
                        help=f"TTS 模型：{'/'.join(MODELS)}（默认取配置，配置无则 s2.1-pro）")


def add_text_args(parser):
    parser.add_argument("--text", help="要合成的文本")
    parser.add_argument("--text-file", help="从 UTF-8 文本文件读取文本（适合长文本）")
    parser.add_argument("-o", "--output", help="输出音频文件路径（默认 tts-<时间戳>.<格式>）")
    parser.add_argument("--reference-id", action="append", metavar="VOICE_ID",
                        help="音色模型 id；传多次则为多说话人（文本需含 <|speaker:0|> 等标记）")
    parser.add_argument("--reference-audio", action="append", metavar="AUDIO",
                        help="零样本克隆参考音频，可多次传入（与 --reference-text 配对）")
    parser.add_argument("--reference-text", action="append", metavar="TEXT",
                        help="参考音频的转录文本，与 --reference-audio 一一对应")
    parser.add_argument("--format", choices=FORMATS, help="输出格式：mp3/wav/pcm/opus")
    parser.add_argument("--mp3-bitrate", type=int, choices=[64, 128, 192],
                        help="MP3 码率 kbps（仅 format=mp3）")
    parser.add_argument("--opus-bitrate", type=int,
                        choices=[-1000, 24000, 32000, 48000, 64000],
                        help="Opus 码率 bps（-1000 自动；仅 format=opus）")
    parser.add_argument("--sample-rate", type=int, help="采样率 Hz（opus 建议 48000）")
    parser.add_argument("--latency", choices=LATENCIES, help="延迟模式：low/normal/balanced")
    parser.add_argument("--chunk-length", type=int, help="分块长度 100-300（越小首音越快）")
    parser.add_argument("--speed", type=float, help="语速 0.5-2.0（1.0 正常）")
    parser.add_argument("--volume", type=float, help="音量 -20 到 20 dB（0 正常，支持小数）")
    parser.add_argument("--temperature", type=float, help="表现力 0-1（越高越多样）")
    parser.add_argument("--top-p", type=float, help="核采样 0-1")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="fish_tts.py",
        description="Fish Audio 文字转语音：零依赖 REST 客户端（POST /v1/tts）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_tts = sub.add_parser("tts", help="文字转语音：POST /v1/tts")
    add_text_args(p_tts)
    common_args(p_tts)
    p_tts.add_argument("--normalize", dest="normalize", action="store_true", default=None,
                       help="开启文本归一化（数字等更稳定，默认开）")
    p_tts.add_argument("--no-normalize", dest="normalize", action="store_false",
                       help="关闭文本归一化")
    p_tts.add_argument("--normalize-loudness", dest="normalize_loudness",
                       action="store_true", default=None,
                       help="开启响度归一化（S2 系列生效，默认开）")
    p_tts.add_argument("--no-normalize-loudness", dest="normalize_loudness",
                       action="store_false", help="关闭响度归一化")
    p_tts.add_argument("--max-new-tokens", type=int, help="每分块最大音频 token（默认 1024）")
    p_tts.add_argument("--repetition-penalty", type=float,
                       help="重复惩罚，>1 减少复读（默认 1.2）")
    p_tts.add_argument("--min-chunk-length", type=int,
                       help="切分新块的最小字符数 0-100（默认 50）")
    p_tts.add_argument("--condition-on-previous", dest="condition_on_previous",
                       action="store_true", default=None,
                       help="用前文音频保持音色一致（默认开）")
    p_tts.add_argument("--no-condition-on-previous", dest="condition_on_previous",
                       action="store_false", help="关闭前文条件")
    p_tts.add_argument("--early-stop-threshold", type=float,
                       help="批处理早停阈值 0-1（默认 1）")
    p_tts.add_argument("--features", help="特性开关，逗号分隔（如 quality-guard）")
    p_tts.set_defaults(func=cmd_tts)

    p_voices = sub.add_parser("voices", help="列出/搜索音色：GET /model")
    p_voices.add_argument("--search", dest="title", metavar="关键词",
                          help="按标题搜索（如 --search 女声）")
    p_voices.add_argument("--tag", help="按标签过滤，多个用逗号分隔")
    p_voices.add_argument("--language", help="按语言过滤（如 zh/en/ja），多个用逗号分隔")
    p_voices.add_argument("--title-language", help="按标题语言过滤")
    p_voices.add_argument("--page-size", type=int, help="每页数量")
    p_voices.add_argument("--page-number", type=int, help="页码（从 1 开始）")
    p_voices.add_argument("--self-only", action="store_true",
                          help="只看自己克隆的音色")
    p_voices.add_argument("--sort-by", choices=["score", "task_count", "created_at"],
                          help="排序字段（默认 score）")
    p_voices.add_argument("--json", action="store_true", help="输出原始 JSON")
    common_args(p_voices)
    p_voices.set_defaults(func=cmd_voices)

    p_cfg = sub.add_parser("config", help="查看当前配置（key 打码显示）")
    p_cfg.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    p_cfg.set_defaults(func=cmd_config)

    p_init = sub.add_parser("init", help="从 config.example.json 生成 config.json")
    p_init.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    p_init.add_argument("--force", action="store_true", help="覆盖已存在的 config.json")
    p_init.set_defaults(func=cmd_init)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except ApiError as exc:
        eprint(f"[error] HTTP {exc.status}：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
