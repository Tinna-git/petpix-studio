"""
PetPix Studio - AI 宠物数字内容服务
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from styles import STYLES, DEFAULT_STYLE
from generator import generate_pet_art
import httpx

load_dotenv()

app = FastAPI(title="PetPix Studio", version="1.0.0")

# 静态文件 & 生成结果
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/outputs", StaticFiles(directory=str(BASE_DIR / "outputs")), name="outputs")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/styles")
async def list_styles():
    return {
        "styles": [
            {"id": k, "name": v["name"], "description": v["description"], "icon": v["icon"]}
            for k, v in STYLES.items()
        ]
    }


@app.post("/api/generate")
async def generate(
    file: UploadFile = File(...),
    style: str = Form(DEFAULT_STYLE),
):
    if style not in STYLES:
        raise HTTPException(status_code=400, detail=f"未知风格: {style}")

    # 读取上传图片
    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")

    style_cfg = STYLES[style]

    try:
        result = await generate_pet_art(
            image_bytes=image_bytes,
            prompt=style_cfg["prompt"],
            n_prompt=style_cfg["n_prompt"],
            strength=style_cfg["strength"],
            image_size=style_cfg["image_size"],
            num_inference_steps=style_cfg["num_inference_steps"],
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"AI 服务错误: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")

    return {"style": style, "serve_url": result["serve_url"], "filename": result["filename"]}


# SPA fallback — 非 API 路径返回 index.html
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    index = BASE_DIR / "static" / "index.html"
    if index.exists():
        from starlette.responses import FileResponse
        return FileResponse(str(index))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
