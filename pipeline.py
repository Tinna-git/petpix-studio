"""
多步生成流水线 - 实现步骤：
1. 特征提取：用视觉模型分析宠物照片，输出详细特征描述
2. 风格化生成：将特征描述 + 风格 prompt 组合，用 Kolors 生成
3. 融合优化：预留（需要额外模型/API支持）

当前实现：步骤 1 + 2
"""

import os
import sys
import json
import time
import uuid
import base64
import urllib.request
import urllib.parse
import ssl

sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

# 加载 .env
def load_env():
    env = {}
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env

env = load_env()
SILICONFLOW_KEY = env.get("SILICONFLOW_API_KEY", "")
DASHSCOPE_KEY = env.get("DASHSCOPE_API_KEY", "")


# ── Step 1: 特征提取 ──

def extract_pet_features(image_path: str) -> dict:
    """
    用 DashScope Qwen-VL 视觉模型分析宠物照片，提取详细特征。
    """
    with open(image_path, "rb") as f:
        img_data = f.read()
    b64 = base64.b64encode(img_data).decode()

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_KEY}",
        "Content-Type": "application/json",
    }

    # 使用 Qwen2.5-VL 视觉模型
    payload = {
        "model": "qwen2.5-vl-7b-instruct",
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个宠物特征分析专家。请仔细观察这张宠物照片，提取以下信息并以 JSON 格式输出：\n"
                    "{\n"
                    '  "species": "猫/狗/其他",\n'
                    '  "breed": "推测的品种",\n'
                    '  "color": "主要毛色描述",\n'
                    '  "markings": "斑纹/花纹特征",\n'
                    '  "eye_color": "眼睛颜色",\n'
                    '  "eye_shape": "眼睛形状",\n'
                    '  "fur_type": "毛发类型(长毛/短毛/卷毛等)",\n'
                    '  "fur_length": "毛发长度描述",\n'
                    '  "body_shape": "体型描述",\n'
                    '  "pose": "当前姿势",\n'
                    '  "expression": "表情描述",\n'
                    '  "ear_shape": "耳朵形状",\n'
                    '  "nose": "鼻子特征",\n'
                    '  "distinctive_features": "独特特征(如白手套、花脸等)",\n'
                    '  "background": "背景环境",\n'
                    '  "detailed_description": "一段详细的外观描述，用于AI绘图prompt，英文，50-80词"\n'
                    "}\n"
                    "只输出 JSON，不要任何其他内容。"
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": "请分析这只宠物的特征。"},
                ],
            },
        ],
        "max_tokens": 2048,
        "temperature": 0.1,
    }

    ctx = ssl.create_default_context()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    print("  [Step 1] 正在分析宠物特征...")
    start = time.time()
    
    with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
        result = json.loads(resp.read().decode())
    
    elapsed = time.time() - start
    content = result["choices"][0]["message"]["content"]
    print(f"  [Step 1] 分析完成 ({elapsed:.1f}s)")
    
    # 尝试解析 JSON
    try:
        # 清理可能的 markdown 代码块
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        # 修复常见 JSON 问题：尾部逗号
        content = content.replace(",\n}", "\n}")
        content = content.replace(",\n]", "\n]")
        features = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"  [Step 1] JSON 解析失败: {e}")
        # 清理控制字符后重试
        try:
            cleaned = content.encode("utf-8", errors="ignore").decode("unicode_escape", errors="ignore")
            cleaned = cleaned.replace("\n", " ").replace("\r", " ").replace("\t", " ")
            # 重新提取 JSON 对象
            import re
            m = re.search(r'\{[^{}]*"detailed_description"[^{}]*\}', cleaned)
            if m:
                cleaned = m.group(0)
            cleaned = cleaned.replace(", }", "}").replace(",}", "}")
            features = json.loads(cleaned)
            print(f"  [Step 1] 清理后解析成功")
        except Exception as e2:
            print(f"  [Step 1] 清理后仍失败: {e2}")
            import re
            m = re.search(r'"detailed_description"\s*:\s*"([^"]+)"', content)
            if m:
                features = {"detailed_description": m.group(1)}
                print(f"  [Step 1] 提取到 detailed_description")
            else:
                print(f"  [Step 1] 原始输出: {content[:300]}")
                features = {"detailed_description": content}
    
    return features


# ── Step 2: 风格化生成（带特征描述） ──

def generate_with_features(
    image_path: str,
    pet_features: dict,
    style_config: dict,
) -> dict:
    """
    结合宠物特征描述和风格 prompt，生成风格化图片。
    """
    with open(image_path, "rb") as f:
        img_data = f.read()
    b64 = base64.b64encode(img_data).decode()
    image_url = f"data:image/jpeg;base64,{b64}"

    # 策略：img2img 时图片本身携带宠物外观，prompt 只管风格
    # 宠物特征用于增强 negative prompt（告诉模型别破坏这些关键特征）
    style_prompt = style_config["prompt"]
    n_prompt = style_config.get("n_prompt", "")

    # 用特征关键词补充 negative prompt，防止模型"过度创作"
    identity_hints = []
    for key in ("breed", "color", "eye_color", "fur_type", "distinctive_features"):
        val = pet_features.get(key, "")
        if val and len(val) < 40:
            identity_hints.append(f"not {val}")
    identity_neg = ", ".join(identity_hints)
    combined_n = f"{n_prompt}, different pet, different breed, changed appearance, different eyes, different fur color, identity lost, {identity_neg}" if identity_hints else f"{n_prompt}, different pet, changed appearance, identity lost"

    # strength: 风格配置值作为基准，再降低以保真
    strength = max(0.2, style_config.get("strength", 0.35) - 0.1)

    url = "https://api.siliconflow.cn/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "Kwai-Kolors/Kolors",
        "prompt": style_prompt,
        "image_url": image_url,
        "image_size": style_config.get("image_size", "1024x1024"),
        "n_prompt": combined_n,
        "strength": strength,
        "num_inference_steps": style_config.get("num_inference_steps", 30),
    }

    ctx = ssl.create_default_context()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    print(f"  [Step 2] 正在生成风格化图片 (strength={strength})...")
    print(f"  [Step 2] Prompt: {style_prompt[:100]}...")
    start = time.time()

    with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
        result = json.loads(resp.read().decode())

    elapsed = time.time() - start
    images = result.get("images", [])
    if not images:
        raise ValueError("API 未返回生成图片")

    generated_url = images[0]["url"]
    print(f"  [Step 2] 生成完成 ({elapsed:.1f}s)")

    filename = f"pipeline_{uuid.uuid4().hex[:12]}_{int(time.time())}.png"

    # 尝试下载到本地（本地开发用，Railway 上可能失败但不影响）
    local_path = None
    try:
        req2 = urllib.request.Request(generated_url)
        with urllib.request.urlopen(req2, timeout=60, context=ctx) as resp:
            img_bytes = resp.read()
        filepath = os.path.join("outputs", filename)
        os.makedirs("outputs", exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(img_bytes)
        local_path = filepath
        print(f"  [Step 2] 已保存: {filepath}")
    except Exception as e:
        print(f"  [Step 2] 本地保存失败（不影响）: {e}")

    return {"local_path": local_path, "filename": filename, "remote_url": generated_url}


# ── 主流程 ──

def pipeline(image_path: str, style_id: str = "guardian"):
    """完整的多步生成流水线"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from styles import STYLES
    style = STYLES.get(style_id, STYLES["guardian"])

    print(f"=== 多步生成流水线 ===")
    print(f"输入图片: {image_path}")
    print(f"风格: {style['name']} ({style['icon']})")
    print()

    # Step 1: 特征提取
    features = extract_pet_features(image_path)
    print(f"  特征摘要: {json.dumps(features, ensure_ascii=False, indent=2)[:300]}...")
    print()

    # Step 2: 风格化生成
    result = generate_with_features(image_path, features, style)
    print()
    print(f"=== 完成！生成图片: {result['local_path']} ===")
    return features, result


if __name__ == "__main__":
    # 测试：用一张已有的输出图作为输入
    test_images = [
        ("outputs/136bafa4f315_1775645864.png", "guardian"),
        ("outputs/guardian_low_strength.png", "guardian"),
    ]
    
    # 用第一张原图风格的测试
    image_path = sys.argv[1] if len(sys.argv) > 1 else test_images[0][0]
    style_id = sys.argv[2] if len(sys.argv) > 2 else test_images[0][1]
    
    pipeline(image_path, style_id)
