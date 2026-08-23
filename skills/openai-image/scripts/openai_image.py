#!/usr/bin/env python3
"""
OpenAI 兼容图像 API 命令行工具（零第三方依赖，仅用 Python 标准库）。

支持两个端点：
  POST {base_url}/images/generations   文生图
  POST {base_url}/images/edits         图片编辑（multipart/form-data）

配置：优先读取 skill 根目录下的 config.json（由 config.example.json 复制而来），
      命令行 --base-url/--api-key/--model 可临时覆盖。

用法示例：
  python openai_image.py generate --prompt "一只戴眼镜的橘猫，水彩风格" -o cat.png
  python openai_image.py edit --image in.png --prompt "把背景换成星空" -o out.png
  python openai_image.py init          # 生成 config.json
  python openai_image.py config        # 查看当前配置（key 打码）
"""

import argparse
import base64
import io
import json
import mimetypes
import os
import sys
import time
import uuid
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-image-1"
DEFAULT_TIMEOUT = 300  # 秒；复杂提示词最长可能接近 2 分钟
MAX_RETRIES = 3

# Windows 下强制 UTF-8 输出，避免控制台 GBK 编码导致中文/JSON 乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_CONFIG_PATH = os.path.join(SKILL_ROOT, "config.json")


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
    except Exception as exc:  # 配置损坏时给出明确提示而不是静默
        raise SystemExit(f"配置文件 {path} 解析失败：{exc}")


def resolve_settings(args):
    cfg = load_config(args.config)
    base_url = (args.base_url or cfg.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
    api_key = args.api_key or cfg.get("api_key") or ""
    model = args.model or cfg.get("model") or DEFAULT_MODEL
    return base_url, api_key, model


def require_api_key(api_key, config_path):
    if not api_key:
        raise SystemExit(
            "未找到 API key。请复制 config.example.json 为 config.json 并填入 api_key，"
            f"或用 --api-key 传入。（配置文件位置：{config_path}）"
        )


def enforce_transparent_format(args):
    """透明背景只支持 png/webp；jpeg 会被 API 拒绝，自动改用 png 并提示。"""
    if args.background == "transparent" and args.output_format == "jpeg":
        eprint("[warn] 透明背景（--background transparent）不支持 jpeg 输出，已自动改用 png（可用 webp）。")
        args.output_format = "png"


def mask_key(key):
    if not key:
        return "(未设置)"
    return key[:6] + "..." + key[-4:] if len(key) > 12 else "***"


# ---------------------------------------------------------------- HTTP

def http_request(url, headers, body=None, timeout=DEFAULT_TIMEOUT):
    """带重试的 HTTP 请求。429/5xx 与网络错误自动退避重试。"""
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
            if status == 429 or status >= 500:
                last_error = (status, raw)
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    eprint(f"[retry] HTTP {status}，{wait}s 后重试（{attempt + 1}/{MAX_RETRIES}）…")
                    time.sleep(wait)
                    continue
            return status, raw
        except Exception as exc:
            last_error = (0, str(exc).encode())
            if attempt < MAX_RETRIES:
                eprint(f"[retry] 网络错误：{exc}（{attempt + 1}/{MAX_RETRIES}）…")
                time.sleep(2 ** attempt)
                continue
            break
    status, raw = last_error
    raise SystemExit(f"请求失败（HTTP {status}）：{raw.decode('utf-8', errors='replace')[:500]}")


def parse_api_response(status, raw):
    """解析响应；出错时抛出带可读提示的 ApiError。"""
    try:
        data = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        if status < 400:
            return {}
        raise ApiError(status, f"非 JSON 响应：{raw.decode('utf-8', errors='replace')[:300]}")

    if status >= 400:
        err = data.get("error", {}) if isinstance(data, dict) else {}
        message = err.get("message") or data.get("message") or f"HTTP {status}"
        code = err.get("code") or data.get("code") or ""
        hint = error_hint(status, code, message)
        raise ApiError(status, f"{message}\n提示：{hint}", data)

    return data


def error_hint(status, code, message):
    if status == 401:
        return "API key 无效或未授权，请检查 config.json 中的 api_key。"
    if status == 404:
        return ("端点或模型不存在。请确认 base_url 指向正确的服务，且该服务支持 "
                "/images/generations 或 /images/edits 端点及所用模型。")
    if status == 429:
        return "限流或配额/余额不足，稍后重试或检查账户额度。"
    if status == 403:
        return "无权限访问该模型（部分模型需完成 API Organization Verification）。"
    if code == "moderation_blocked":
        return "提示词或生成结果触发内容审核，请改写提示词后再试。"
    if message:
        return message
    return f"HTTP {status}，详见上方响应信息。"


# ---------------------------------------------------------------- 图片保存

def detect_image_ext(raw):
    """根据文件头魔数判断 png/jpeg/webp，失败返回 png。"""
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if raw[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    return "png"


def fetch_url(url, timeout=DEFAULT_TIMEOUT):
    """dall-e-2/3 在 response_format=url 时返回临时 URL，需要下载。"""
    req = urllib.request.Request(url, headers={"User-Agent": "openai-image-skill/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def decide_output_paths(args_output, count, ext):
    """决定输出路径列表。count=1 且指定文件名时用原名；多张图时输出到目录。"""
    if args_output:
        is_dir = os.path.isdir(args_output) or count > 1
        if is_dir:
            os.makedirs(args_output, exist_ok=True)
            return [os.path.join(args_output, f"image-{i}.{ext}") for i in range(count)]
        return [args_output]
    if count == 1:
        return [f"image-{int(time.time())}.{ext}"]
    out_dir = f"image-{int(time.time())}"
    os.makedirs(out_dir, exist_ok=True)
    return [os.path.join(out_dir, f"image-{i}.{ext}") for i in range(count)]


def save_images(data, args_output, prefer_ext):
    """保存 data[].b64_json 或 data[].url，返回保存的文件路径列表。"""
    items = data.get("data") or []
    if not items:
        raise SystemExit("响应中没有图片数据（data 为空）。")

    saved, ext = [], prefer_ext
    # 先解析出全部字节，统一确定扩展名
    blobs = []
    for item in items:
        if item.get("b64_json"):
            blobs.append(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            eprint(f"[info] 下载图片：{item['url']}")
            blobs.append(fetch_url(item["url"]))
        else:
            raise SystemExit(f"图片条目中既无 b64_json 也无 url：{json.dumps(item)[:200]}")
    ext = ext or detect_image_ext(blobs[0])

    for path, blob in zip(decide_output_paths(args_output, len(blobs), ext), blobs):
        with open(path, "wb") as f:
            f.write(blob)
        eprint(f"[saved] {path}（{len(blob)} bytes）")
        saved.append(path)
    return saved


def build_summary(data, saved_paths):
    summary = {"saved": saved_paths}
    for key in ("model", "created", "output_format", "size", "usage"):
        if key in data:
            summary[key] = data[key]
    if data.get("data") and data["data"][0].get("revised_prompt"):
        summary["revised_prompt"] = data["data"][0]["revised_prompt"]
    return summary


# ---------------------------------------------------------------- multipart

def build_multipart(fields, files):
    """手工构造 multipart/form-data（标准库没有现成实现）。"""
    boundary = "----openai-image-" + uuid.uuid4().hex
    buf = io.BytesIO()
    for name, value in fields.items():
        buf.write(f"--{boundary}\r\n".encode())
        buf.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        buf.write(str(value).encode())
        buf.write(b"\r\n")
    for name, filepath in files:
        filename = os.path.basename(filepath)
        ctype = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
        with open(filepath, "rb") as f:
            content = f.read()
        buf.write(f"--{boundary}\r\n".encode())
        buf.write(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        )
        buf.write(f"Content-Type: {ctype}\r\n\r\n".encode())
        buf.write(content)
        buf.write(b"\r\n")
    buf.write(f"--{boundary}--\r\n".encode())
    return buf.getvalue(), boundary


# ---------------------------------------------------------------- 子命令

def common_args(parser):
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH,
                        help="配置文件路径（默认：skill 目录下的 config.json）")
    parser.add_argument("--base-url", help="覆盖配置中的 base_url")
    parser.add_argument("--api-key", help="覆盖配置中的 api_key")
    parser.add_argument("--model", help="覆盖配置中的 model")
    parser.add_argument("-o", "--output",
                        help="输出文件路径；生成多张（n>1）或已存在的目录时按目录处理")
    parser.add_argument("--size", help="如 1024x1024 / 1024x1536 / 1536x1024 / auto")
    parser.add_argument("--quality", choices=["low", "medium", "high", "auto"],
                        help="low/medium/high/auto")
    parser.add_argument("--output-format", choices=["png", "webp", "jpeg"],
                        help="输出格式，默认 png")
    parser.add_argument("--background", choices=["transparent", "opaque", "auto"],
                        help="背景：transparent/opaque/auto")
    parser.add_argument("--moderation", choices=["auto", "low"],
                        help="审核强度：auto（默认）/ low")
    parser.add_argument("--response-format", choices=["b64_json", "url"],
                        help="dall-e-2/3 的返回格式；gpt-image 系列恒为 b64_json")
    parser.add_argument("--n", type=int, default=1, help="生成张数（默认 1）")


def read_prompt(args):
    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return args.prompt


def add_prompt_args(parser):
    parser.add_argument("--prompt", help="提示词")
    parser.add_argument("--prompt-file", help="从 UTF-8 文本文件读取提示词")


def cmd_generate(args):
    base_url, api_key, model = resolve_settings(args)
    require_api_key(api_key, args.config)
    enforce_transparent_format(args)

    prompt = read_prompt(args)
    if not prompt:
        raise SystemExit("缺少提示词：请用 --prompt 或 --prompt-file 提供。")

    payload = {"model": model, "prompt": prompt, "n": args.n}
    if args.size:
        payload["size"] = args.size
    if args.quality:
        payload["quality"] = args.quality
    if args.output_format:
        payload["output_format"] = args.output_format
    if args.background:
        payload["background"] = args.background
    if args.moderation:
        payload["moderation"] = args.moderation
    # dall-e 系列默认返回 URL；脚本统一要求 b64_json 以便直接落盘
    response_format = args.response_format or ("b64_json" if model.startswith("dall-e") else None)
    if response_format:
        payload["response_format"] = response_format

    eprint(f"[info] POST {base_url}/images/generations  model={model}  n={payload['n']}")
    status, raw = http_request(
        f"{base_url}/images/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        body=json.dumps(payload).encode(),
    )
    data = parse_api_response(status, raw)
    saved = save_images(data, args.output, args.output_format)
    print(json.dumps(build_summary(data, saved), ensure_ascii=False, indent=2))


def cmd_edit(args):
    base_url, api_key, model = resolve_settings(args)
    require_api_key(api_key, args.config)
    enforce_transparent_format(args)

    prompt = read_prompt(args)
    if not prompt:
        raise SystemExit("缺少提示词：请用 --prompt 或 --prompt-file 提供。")

    if not args.image:
        raise SystemExit("edit 需要至少一个 --image 输入图片。")
    for p in args.image:
        if not os.path.isfile(p):
            raise SystemExit(f"输入图片不存在：{p}")
    if args.mask and not os.path.isfile(args.mask):
        raise SystemExit(f"mask 图片不存在：{args.mask}")

    fields = {"model": model, "prompt": prompt, "n": args.n}
    if args.size:
        fields["size"] = args.size
    if args.quality:
        fields["quality"] = args.quality
    if args.output_format:
        fields["output_format"] = args.output_format
    if args.background:
        fields["background"] = args.background
    if args.moderation:
        fields["moderation"] = args.moderation
    response_format = args.response_format or ("b64_json" if model.startswith("dall-e") else None)
    if response_format:
        fields["response_format"] = response_format

    files = [("image[]", p) for p in args.image]
    if args.mask:
        files.append(("mask", args.mask))
    body, boundary = build_multipart(fields, files)

    eprint(f"[info] POST {base_url}/images/edits  model={model}  images={len(args.image)}")
    status, raw = http_request(
        f"{base_url}/images/edits",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        body=body,
    )
    data = parse_api_response(status, raw)
    saved = save_images(data, args.output, args.output_format)
    print(json.dumps(build_summary(data, saved), ensure_ascii=False, indent=2))


def cmd_config(args):
    cfg = load_config(args.config)
    base_url = args.base_url or cfg.get("base_url") or DEFAULT_BASE_URL
    api_key = args.api_key or cfg.get("api_key") or ""
    model = args.model or cfg.get("model") or DEFAULT_MODEL
    print(json.dumps({
        "config_path": args.config,
        "exists": os.path.isfile(args.config),
        "base_url": base_url,
        "model": model,
        "api_key": mask_key(api_key),
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
    eprint(f"[info] 已创建 {args.config}，请填入你的 api_key 与 base_url。")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="openai_image.py",
        description="OpenAI 兼容图像 API：文生图与图片编辑（零依赖，标准库实现）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="文生图：POST /images/generations")
    add_prompt_args(p_gen)
    common_args(p_gen)
    p_gen.set_defaults(func=cmd_generate)

    p_edit = sub.add_parser("edit", help="图片编辑：POST /images/edits（multipart）")
    add_prompt_args(p_edit)
    p_edit.add_argument("--image", action="append", required=True,
                        help="输入图片路径，可多次传入（多张参考图/连续编辑）")
    p_edit.add_argument("--mask", help="可选遮罩图片（PNG 且带 alpha 通道）")
    common_args(p_edit)
    p_edit.set_defaults(func=cmd_edit)

    p_cfg = sub.add_parser("config", help="查看当前配置（key 打码显示）")
    p_cfg.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    p_cfg.add_argument("--base-url")
    p_cfg.add_argument("--api-key")
    p_cfg.add_argument("--model")
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
        eprint(f"[error] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
