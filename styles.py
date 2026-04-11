"""
风格配置 - 定义可用的宠物艺术照风格
"""

STYLES = {
    "guardian": {
        "id": "guardian",
        "name": "守护神",
        "description": "神圣守护神风格，让你的宠物化身威严的守护灵兽",
        "icon": "🛡️",
        "prompt": (
            "A majestic guardian spirit portrait of a pet, divine ethereal aura, "
            "golden sacred light rays, celestial armor ornaments, noble and powerful posture, "
            "ethereal mist background, fantasy art style, ultra detailed, 8k, masterpiece"
        ),
        "n_prompt": (
            "blurry, low quality, deformed, ugly, bad anatomy, watermark, text, "
            "extra limbs, extra fingers, mutated, disfigured, cloned face"
        ),
        "strength": 0.6,
        "image_size": "1024x1024",
        "num_inference_steps": 25,
    },
    "mid_autumn": {
        "id": "mid_autumn",
        "name": "中秋限定",
        "description": "花好月圆中秋夜，毛孩子陪你赏月吃月饼",
        "icon": "🌙",
        "prompt": (
            "A pet sitting peacefully under a bright full moon, Chinese Mid-Autumn Festival theme, "
            "glowing moonlight, osmanthus flowers floating in the air, traditional Chinese lanterns, "
            "warm golden tones, mooncakes nearby, dreamy night sky with stars, "
            "illustration style, warm and cozy atmosphere, ultra detailed, 8k"
        ),
        "n_prompt": (
            "blurry, low quality, deformed, ugly, bad anatomy, watermark, text, "
            "scary, dark horror, extra limbs, mutated"
        ),
        "strength": 0.5,
        "image_size": "1024x1024",
        "num_inference_steps": 25,
    },
}

DEFAULT_STYLE = "guardian"
