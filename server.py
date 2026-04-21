"""
PetPix Studio MVP - 纯标准库版本（无需 pip install）
启动：python server.py
"""

import os
import sys
import json
import uuid
import time
import random
import base64
import mimetypes
import urllib.request
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError

# 确保工作目录正确
sys.path.insert(0, str(Path(__file__).parent))

# 加载 .env
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

# ── 配置 ──
PORT = int(os.getenv("PORT", 8000))
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# DashScope (阿里云百炼) - 主力 API
DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/images/generations"
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_MODEL = "wanx2.1-t2i-turbo"

# SiliconFlow - fallback
SILICONFLOW_API_URL = "https://api.siliconflow.cn/v1/images/generations"
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_MODEL = "Kwai-Kolors/Kolors"

# ── 公网 URL 配置（Railway 部署时自动获取） ──
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")  # 手动设置，如 https://xxx.up.railway.app
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")  # Railway 自动注入

STYLES = {
    "guardian": {
        "name": "守护神", "icon": "🛡️",
        "description": "神圣守护神风格，让爱宠（或你和爱宠）化身威严的守护灵兽",
        "prompt": (
            "A golden chinchilla kitten, cream-golden fluffy fur, large round blue-green eyes, "
            "transformed into a majestic guardian deity cat, enormous size, divine ethereal golden aura, "
            "sitting on sacred clouds with lotus flowers, Chinese mythology style, epic, ultra detailed, 8k, masterpiece"
        ),
        "prompt_portrait": (
            "A young Chinese woman and her golden chinchilla kitten companion, "
            "both transformed into majestic guardian deity warriors, divine ethereal golden aura surrounding them, "
            "the woman wearing ornate mythological golden armor with flowing silk ribbons, the cat enormous and regal beside her, "
            "sitting together on sacred clouds with lotus flowers and celestial light, "
            "protective stance, sacred bond between human and pet, Chinese mythology style, epic, ultra detailed, 8k, masterpiece"
        ),
        "support_portrait": True,
        "n_prompt": "blurry, low quality, deformed, ugly, bad anatomy, watermark, text, extra limbs, mutated, dog, puppy, different breed",
        "strength": 0.35,
        "num_inference_steps": 30,
    },
    "dragon_boat": {
        "name": "端午限定", "icon": "🌙",
        "description": "浓情端午，毛孩子化身龙舟小勇士",
        "prompt": (
            "A golden chinchilla kitten, cream-golden fluffy fur, large round blue-green eyes, "
            "wearing traditional Chinese clothing with dragon boat festival motifs, sitting beside zongzi rice dumplings, "
            "dragon boat race in background, river scene, festive atmosphere, warm tones, red and green decorations, "
            "Chinese Dragon Boat Festival theme, illustration style, ultra detailed, 8k, masterpiece"
        ),
        "n_prompt": "blurry, low quality, deformed, ugly, bad anatomy, watermark, text, scary, dark horror, extra limbs, mutated, dog, puppy",
        "strength": 0.3,
        "num_inference_steps": 30,
    },
    "royal": {
        "name": "皇家贵族", "icon": "👸",
        "description": "雍容华贵皇家风范，你的宠物就是小王子小公主",
        "prompt": (
            "A golden chinchilla kitten, cream-golden fluffy fur, large round blue-green eyes, "
            "wearing an ornate royal crown and luxurious velvet cape, sitting on an elegant golden throne, "
            "European royal palace interior with crystal chandeliers, oil painting style, Renaissance art, "
            "regal, majestic, rich colors, Baroque style, ultra detailed, 8k, masterpiece"
        ),
        "n_prompt": "blurry, low quality, deformed, ugly, bad anatomy, watermark, text, modern, casual, extra limbs, mutated, dog, puppy",
        "strength": 0.35,
        "num_inference_steps": 30,
    },
    "hanfu": {
        "name": "中式汉服国风", "icon": "👘",
        "description": "穿越千年，毛孩子穿上汉服翩翩起舞",
        "prompt": (
            "A golden chinchilla kitten, cream-golden fluffy fur, large round blue-green eyes, "
            "wearing exquisite Chinese Hanfu traditional dress with flowing silk ribbons, "
            "standing in a classical Chinese garden with plum blossoms, willow trees, and a stone bridge, "
            "ink wash painting mixed with realistic style, Chinese national style, ethereal, poetic, "
            "cherry blossom petals falling, ultra detailed, 8k, masterpiece"
        ),
        "n_prompt": "blurry, low quality, deformed, ugly, bad anatomy, watermark, text, modern, western, extra limbs, mutated, dog, puppy",
        "strength": 0.3,
        "num_inference_steps": 30,
    },
    "korean": {
        "name": "韩系画报爱豆风", "icon": "💖",
        "description": "韩系杂志封面风格，宠物秒变顶流爱豆",
        "prompt": (
            "A golden chinchilla kitten, cream-golden fluffy fur, large round blue-green eyes, "
            "in Korean magazine cover photoshoot style, soft pastel pink and lavender background, "
            "professional studio lighting, fashion editorial aesthetic, wearing cute accessories, "
            "K-pop idol vibe, dreamy soft focus, clean minimal composition, Vogue magazine style, ultra detailed, 8k, masterpiece"
        ),
        "n_prompt": "blurry, low quality, deformed, ugly, bad anatomy, watermark, text, dark, harsh lighting, extra limbs, mutated, dog, puppy",
        "strength": 0.35,
        "num_inference_steps": 30,
    },
    "moonfairy": {
        "name": "月光精灵仙气氛围风", "icon": "🧚",
        "description": "月光下的精灵，给毛孩子披上梦幻仙气",
        "prompt": (
            "A golden chinchilla kitten, cream-golden fluffy fur, large round blue-green eyes, "
            "as a magical moonlight fairy, surrounded by glowing fireflies and soft moonbeams, "
            "sitting on a crescent moon, silver and blue sparkle particles, dreamy night sky with stars, "
            "ethereal glow, fantasy illustration, magical atmosphere, soft bokeh, ultra detailed, 8k, masterpiece"
        ),
        "n_prompt": "blurry, low quality, deformed, ugly, bad anatomy, watermark, text, scary, dark horror, extra limbs, mutated, dog, puppy",
        "strength": 0.3,
        "num_inference_steps": 30,
    },
}

# 导入 pipeline（两步流水线：特征提取 + 风格化生成）
from pipeline import extract_pet_features, generate_with_features

# 导入 mock 订单系统
from mock_order import (
    init_db, create_order, pay_order, get_order, list_orders,
    create_share_link, update_order_style_name, save_generation,
    get_stats, PRICING, DB_PATH
)


def _get_mock_images():
    """获取 outputs 目录下的所有图片文件名"""
    valid_ext = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    return [f.name for f in OUTPUT_DIR.iterdir() if f.suffix.lower() in valid_ext]


def _get_public_image_url(image_bytes: bytes, filename: str) -> str:
    """
    获取图片的公网可访问 URL。
    策略：保存到 uploads/ 目录 → 通过服务器自身公网地址提供访问。
    Railway 部署时使用 RAILWAY_PUBLIC_DOMAIN，本地开发使用 base64。
    """
    # 保存到 uploads 目录
    filepath = UPLOAD_DIR / filename
    filepath.write_bytes(image_bytes)

    # 构建公网 URL
    base = PUBLIC_BASE_URL or RAILWAY_PUBLIC_DOMAIN
    if base:
        if not base.startswith("http"):
            base = f"https://{base}"
        url = f"{base.rstrip('/')}/uploads/{filename}"
        print(f"[Upload] 公网 URL: {url}")
        return url

    # 本地开发 fallback: base64 data URI
    print("[Upload] 无公网域名，使用 base64 data URI（仅本地 mock 可用）")
    b64 = base64.b64encode(image_bytes).decode()
    return f"data:image/jpeg;base64,{b64}"


def _dashscope_generate(image_bytes: bytes, style_id: str, with_owner: bool = False) -> dict:
    """调用阿里云 DashScope API，使用 ref_image 实现图生图"""
    style = STYLES.get(style_id)
    if not style:
        raise ValueError(f"未知风格: {style_id}")

    prompt = style.get("prompt_portrait", style["prompt"]) if with_owner else style["prompt"]

    # 上传图片获取公网 URL
    image_url = _get_public_image_url(image_bytes, "pet.jpg")

    payload = json.dumps({
        "model": DASHSCOPE_MODEL,
        "prompt": style["prompt"],
        "n": 1,
        "size": "1024*1024",
        "ref_image": image_url,
    }).encode()

    req = urllib.request.Request(DASHSCOPE_API_URL, data=payload, headers={
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    })

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())

    # DashScope 返回格式：{"output": {"results": [{"url": "..."}]}, "request_id": "..."}
    output = result.get("output", {})
    results = output.get("results", [])
    if not results:
        # 兼容 OpenAI 格式：{"data": [{"url": "..."}]}
        data = result.get("data", [])
        if not data:
            raise ValueError("DashScope API 未返回生成图片")
        generated_url = data[0].get("url", "")
    else:
        generated_url = results[0].get("url", "")

    if not generated_url:
        raise ValueError("DashScope API 返回图片 URL 为空")

    return {"image_url": generated_url, "filename": f"{uuid.uuid4().hex[:12]}_{int(time.time())}.png", "mock": False}


def _pipeline_generate(image_bytes: bytes, style_id: str, with_owner: bool = False) -> dict:
    """新流水线：Step 1 特征提取 + Step 2 风格化生成"""
    import tempfile
    style = STYLES.get(style_id)
    if not style:
        raise ValueError(f"未知风格: {style_id}")

    # 先保存上传图片到临时文件，pipeline 需要文件路径
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, dir=str(UPLOAD_DIR))
    tmp.write(image_bytes)
    tmp.close()

    try:
        features = extract_pet_features(tmp.name)
        # 从 styles.py 导入的 STYLES 或 server 内置的 STYLES 都有相同字段
        result = generate_with_features(tmp.name, features, style)
        # 部署环境优先用远程 URL（SiliconFlow CDN），本地开发优先用本地路径
        remote_url = result.get("remote_url", "")
        local_path = result.get("local_path", "")
        if PUBLIC_BASE_URL or RAILWAY_PUBLIC_DOMAIN:
            # 部署环境：用远程 URL，同时下载到本地备用
            if remote_url:
                return {"image_url": remote_url, "filename": result["filename"], "mock": False}
            elif local_path and os.path.exists(local_path):
                return {"serve_url": f"/outputs/{result['filename']}", "filename": result["filename"], "mock": False}
        else:
            # 本地开发：优先本地路径
            if local_path and os.path.exists(local_path):
                return {"serve_url": f"/outputs/{result['filename']}", "filename": result["filename"], "mock": False}
            elif remote_url:
                return {"image_url": remote_url, "filename": result["filename"], "mock": False}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def generate_pet_art(image_bytes: bytes, style_id: str, with_owner: bool = False) -> dict:
    """生成宠物艺术照：Pipeline 优先 → DashScope fallback → mock"""
    # 1. Pipeline（需要 SILICONFLOW_KEY 和 DASHSCOPE_KEY）
    if SILICONFLOW_API_KEY and DASHSCOPE_API_KEY:
        try:
            result = _pipeline_generate(image_bytes, style_id, with_owner=with_owner)
            print(f"[Pipeline] 生成成功: {result['filename']}")
            return result
        except Exception as e:
            print(f"[Pipeline] 调用失败: {e}")

    # 2. Fallback 到 DashScope 单步
    if DASHSCOPE_API_KEY:
        try:
            result = _dashscope_generate(image_bytes, style_id, with_owner=with_owner)
            print(f"[DashScope] 生成成功: {result['filename']}")
            return result
        except Exception as e:
            print(f"[DashScope] 调用失败: {e}")

    # 3. 最终 fallback: mock
    print("[Mock] 所有 API 失败，使用 mock 模式")
    return _mock_generate(style_id)


def _mock_generate(style_id: str) -> dict:
    """Mock 生成：随机返回已有图片，模拟延迟"""
    mock_images = _get_mock_images()
    delay = random.uniform(5, 10)
    time.sleep(delay)

    if mock_images:
        filename = random.choice(mock_images)
        return {"filename": filename, "serve_url": f"/outputs/{filename}", "mock": True}
    else:
        return {"filename": "placeholder.png", "serve_url": "", "mock": True, "placeholder": True}


class PetPixHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type=None):
        if not filepath.exists():
            self.send_error(404)
            return
        data = filepath.read_bytes()
        ct = content_type or mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/api/health":
            stats = get_stats()
            self._send_json({"status": "ok", "version": "1.3.0", "mode": "pipeline+api", "stats": stats})
        elif path == "/api/styles":
            self._send_json({"styles": [
                {
                    "id": k, "name": v["name"], "icon": v["icon"],
                    "description": v["description"],
                    "support_portrait": v.get("support_portrait", False),
                }
                for k, v in STYLES.items()
            ]})
        elif path == "/api/pricing":
            self._send_json({"packages": PRICING})
        elif path == "/api/orders":
            self._send_json({"orders": list_orders()})
        elif path.startswith("/api/order/"):
            order_id = path.split("/")[-1]
            self._send_json(get_order(order_id))
        elif path.startswith("/uploads/"):
            filename = path.split("/")[-1]
            self._send_file(UPLOAD_DIR / filename)
        elif path.startswith("/outputs/"):
            filename = path.split("/")[-1]
            self._send_file(OUTPUT_DIR / filename)
        elif path.startswith("/static/"):
            # serve files from static/ subdirectory (e.g. /static/previews/xxx.jpg)
            rel = path[len("/static/"):]
            self._send_file(STATIC_DIR / rel)
        elif path == "/":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        else:
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/api/generate":
            self._handle_generate()
        elif path == "/api/order/create":
            self._handle_create_order()
        elif path == "/api/order/pay":
            self._handle_pay()
        elif path == "/api/share":
            self._handle_share()
        else:
            self._send_json({"error": "Not found"}, 404)

    def _handle_generate(self):
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        boundary = content_type.split("boundary=")[-1].strip()
        parts = body.split(b"--" + boundary.encode())

        image_bytes = None
        style_id = "guardian"
        with_owner = False

        for part in parts:
            if b"Content-Disposition" not in part:
                continue
            part_str = part.decode("utf-8", errors="ignore")
            if 'name="file"' in part_str:
                header_end = part.find(b"\r\n\r\n")
                if header_end >= 0:
                    image_bytes = part[header_end + 4:].rstrip(b"\r\n--")
            elif 'name="style"' in part_str:
                header_end = part.find(b"\r\n\r\n")
                if header_end >= 0:
                    style_id = part[header_end + 4:].decode().strip().strip('"').strip()
            elif 'name="portrait"' in part_str:
                header_end = part.find(b"\r\n\r\n")
                if header_end >= 0:
                    with_owner = part[header_end + 4:].decode().strip().strip('"').strip().lower() in ("true", "1", "yes")

        if not image_bytes:
            self._send_json({"error": "未上传图片"}, 400)
            return

        if style_id not in STYLES:
            self._send_json({"error": f"未知风格: {style_id}"}, 400)
            return

        try:
            result = generate_pet_art(image_bytes, style_id, with_owner=with_owner)
            # 保存生成记录到数据库
            save_generation(
                style_id=style_id,
                filename=result.get("filename", ""),
                image_url=result.get("image_url", result.get("serve_url", "")),
                mock=result.get("mock", False),
            )
            self._send_json({"style": style_id, "portrait": with_owner, **result})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_create_order(self):
        data = self._read_json_body()
        package_id = data.get("package_id", "")
        style_id = data.get("style_id", "")
        image_url = data.get("image_url", "")
        result = create_order(package_id, style_id, image_url=image_url)
        # 注入 style_name
        if style_id in STYLES and "error" not in result:
            update_order_style_name(result["order_id"], STYLES[style_id]["name"])
        if "error" in result:
            self._send_json(result, 400)
        else:
            self._send_json(result)

    def _handle_pay(self):
        data = self._read_json_body()
        order_id = data.get("order_id", "")
        method = data.get("method", "wechat")
        result = pay_order(order_id, method)
        if "error" in result:
            self._send_json(result, 404)
        else:
            self._send_json(result)

    def _handle_share(self):
        data = self._read_json_body()
        order_id = data.get("order_id", "")
        result = create_share_link(order_id)
        if "error" in result:
            self._send_json(result, 404)
        else:
            self._send_json(result)

    def log_message(self, format, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {args[0]}")


if __name__ == "__main__":
    init_db()
    stats = get_stats()
    print(f"PetPix Studio v1.3 running at http://localhost:{PORT}")
    print(f"Public URL: {PUBLIC_BASE_URL or RAILWAY_PUBLIC_DOMAIN or '(local only)'}")
    print(f"Mock images: {len(_get_mock_images())} found in outputs/")
    print(f"Orders: {stats['total_orders']} total, {stats['paid_orders']} paid, ¥{stats['total_revenue']} revenue")
    print(f"Generations: {stats['total_generations']} total ({stats['real_generations']} real)")
    print(f"Database: {DB_PATH}")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), PetPixHandler)
    server.serve_forever()
