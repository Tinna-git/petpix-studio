"""
图生图核心逻辑 - 调用硅基流动 Kwai-Kolors/Kolors API
"""

import os
import uuid
import time
import base64
import httpx

from pathlib import Path

API_URL = "https://api.siliconflow.cn/v1/images/generations"
API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
MODEL = "Kwai-Kolors/Kolors"
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


async def generate_pet_art(
    image_bytes: bytes,
    prompt: str,
    n_prompt: str = "",
    strength: float = 0.6,
    image_size: str = "1024x1024",
    num_inference_steps: int = 25,
) -> dict:
    """
    上传宠物照片，调用图生图 API 生成艺术照。

    Args:
        image_bytes: 原始图片字节数据
        prompt: 正向提示词
        n_prompt: 反向提示词
        strength: 变化强度 (0-1)
        image_size: 输出图片尺寸
        num_inference_steps: 推理步数

    Returns:
        dict: {"local_path": str, "filename": str, "serve_url": str}
    """
    # 编码为 base64 data URI
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:image/jpeg;base64,{b64}"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "image_url": image_url,
        "image_size": image_size,
        "n_prompt": n_prompt,
        "strength": strength,
        "num_inference_steps": num_inference_steps,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        result = resp.json()

    # 提取生成图片 URL
    images = result.get("images", [])
    if not images:
        raise ValueError("API 未返回生成图片")

    generated_url = images[0]["url"]

    # 立即下载到本地（URL 1小时过期）
    async with httpx.AsyncClient(timeout=60.0) as client:
        img_resp = await client.get(generated_url)
        img_resp.raise_for_status()

    # 保存到本地
    filename = f"{uuid.uuid4().hex[:12]}_{int(time.time())}.png"
    filepath = OUTPUT_DIR / filename
    filepath.write_bytes(img_resp.content)

    return {
        "local_path": str(filepath),
        "filename": filename,
        "serve_url": f"/outputs/{filename}",
    }
