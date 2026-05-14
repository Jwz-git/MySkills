#!/usr/bin/env python3
"""
图片预处理入口脚本 - 用于 img2md skill
自动检测图片尺寸，决定直接读取还是裁剪，输出待处理的文件列表。
Agent 只需运行此脚本，然后读取输出的文件列表即可。
"""

import sys
import os
import json
import subprocess
from pathlib import Path

# ─── 自动安装依赖 ───────────────────────────────────────
def _ensure_dependencies():
    """检查并自动安装缺失的依赖库"""
    missing = []
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")
    try:
        import numpy as np
    except ImportError:
        missing.append("numpy")

    if missing:
        print(f"[img2md] 正在安装缺失依赖: {', '.join(missing)} ...", file=sys.stderr)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + missing + ["--break-system-packages", "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[img2md] 依赖安装完成", file=sys.stderr)

_ensure_dependencies()

from PIL import Image

# ─── 导入裁剪模块（使用绝对路径，避免相对导入问题） ────
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from split_image import split_image


# ─── 配置 ───────────────────────────────────────────────
HEIGHT_THRESHOLD = 1500   # 高度超过此值则裁剪
TARGET_HEIGHT = 1000      # 每个片段的目标高度
OVERLAP = 150             # 片段间重叠像素
# ────────────────────────────────────────────────────────


def get_image_info(image_path):
    """获取图片尺寸信息"""
    img = Image.open(image_path)
    width, height = img.size
    return {"width": width, "height": height, "format": img.format, "mode": img.mode}


def prepare(input_path, output_dir=None):
    """
    主入口：检测图片 → 决定是否裁剪 → 输出待处理文件列表

    Args:
        input_path: 输入图片路径
        output_dir: 输出目录（默认为图片所在目录下的子文件夹）

    Returns:
        dict: 包含图片信息和待处理文件列表
    """
    input_path = Path(input_path).resolve()

    if not input_path.exists():
        result = {"error": f"图片不存在: {input_path}"}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # 1. 获取图片信息
    info = get_image_info(input_path)
    width, height = info["width"], info["height"]

    # 2. 判断是否需要裁剪
    needs_split = height > HEIGHT_THRESHOLD

    if not needs_split:
        result = {
            "needs_split": False,
            "image_info": info,
            "message": f"图片高度 {height}px，无需裁剪，直接读取即可",
            "files_to_read": [str(input_path)]
        }
    else:
        # 3. 执行裁剪（调用 split_image.py）
        if output_dir is None:
            output_dir = str(input_path.parent / f"{input_path.stem}_split")

        segments = split_image(
            str(input_path),
            output_dir,
            max_height=TARGET_HEIGHT,
            overlap=OVERLAP,
            height_threshold=HEIGHT_THRESHOLD
        )

        result = {
            "needs_split": True,
            "image_info": info,
            "message": f"图片高度 {height}px，已裁剪为 {len(segments)} 个片段",
            "split_output_dir": output_dir,
            "files_to_read": segments
        }

    # 输出 JSON 结果
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python prepare_image.py <图片路径> [输出目录]")
        print()
        print("功能: 自动检测图片尺寸，判断是否需要裁剪，输出待处理的文件列表。")
        print()
        print("输出为 JSON 格式，包含:")
        print("  - needs_split: 是否进行了裁剪")
        print("  - image_info:  图片尺寸信息")
        print("  - files_to_read: 待读取的文件路径列表")
        sys.exit(1)

    image_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None
    prepare(image_path, out_dir)


if __name__ == "__main__":
    main()
