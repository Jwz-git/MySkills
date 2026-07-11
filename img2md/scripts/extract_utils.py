#!/usr/bin/env python3
"""
图片裁剪与打包工具 - 用于 img2md skill
提供两个主要功能：
1. crop: 从输入图片中裁剪出指定区域，并保存到指定位置（通常是 img/ 目录）。支持绝对像素值和归一化坐标(0-1或0-1000)。
2. zip: 将 Markdown 文件和同级的 img/ 目录整体打包为 ZIP 文件。
"""

import sys
import os
import zipfile
from pathlib import Path

def _ensure_dependencies():
    """检查并自动安装 Pillow 依赖库"""
    try:
        from PIL import Image
    except ImportError:
        import subprocess
        print("[img2md] 正在安装 Pillow ...", file=sys.stderr)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "Pillow", "--break-system-packages", "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

def crop_image(image_path, output_path, left, top, right, bottom):
    """
    裁剪图片指定区域并保存
    """
    _ensure_dependencies()
    from PIL import Image

    image_path = Path(image_path).resolve()
    output_path = Path(output_path).resolve()

    if not image_path.exists():
        print(f"错误: 输入图片不存在: {image_path}", file=sys.stderr)
        sys.exit(1)

    # 自动创建输出目录
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(image_path)
    width, height = img.size

    # 判断坐标类型并转换
    # 如果坐标都在 0 到 1 之间，认为是归一化坐标 [0, 1]
    if all(0.0 <= c <= 1.0 for c in (left, top, right, bottom)):
        left_px = int(left * width)
        top_px = int(top * height)
        right_px = int(right * width)
        bottom_px = int(bottom * height)
    # 如果坐标都在 0 到 1000 之间，且有大于 1 的数，认为是归一化坐标 [0, 1000]
    elif any(c > 1.0 for c in (left, top, right, bottom)) and all(0.0 <= c <= 1000.0 for c in (left, top, right, bottom)):
        left_px = int((left / 1000.0) * width)
        top_px = int((top / 1000.0) * height)
        right_px = int((right / 1000.0) * width)
        bottom_px = int((bottom / 1000.0) * height)
    else:
        # 否则作为绝对像素坐标处理
        left_px = int(left)
        top_px = int(top)
        right_px = int(right)
        bottom_px = int(bottom)

    # 边界限制
    left_px = max(0, min(left_px, width))
    top_px = max(0, min(top_px, height))
    right_px = max(0, min(right_px, width))
    bottom_px = max(0, min(bottom_px, height))

    if left_px >= right_px or top_px >= bottom_px:
        print(f"错误: 无效的裁剪范围 ({left_px}, {top_px}, {right_px}, {bottom_px})", file=sys.stderr)
        sys.exit(1)

    cropped = img.crop((left_px, top_px, right_px, bottom_px))
    # 默认保存为 PNG 以保留无损画质
    cropped.save(output_path, "PNG")
    print(f"已成功裁剪区域并保存至: {output_path}")


def package_zip(md_path, zip_path=None):
    """
    将 Markdown 文件和同级的 img/ 目录打包为 ZIP
    """
    md_path = Path(md_path).resolve()
    if not md_path.exists():
        print(f"错误: Markdown 文件不存在: {md_path}", file=sys.stderr)
        sys.exit(1)

    if zip_path is None:
        zip_path = md_path.with_suffix(".zip")
    else:
        zip_path = Path(zip_path).resolve()

    parent_dir = md_path.parent
    img_dir = parent_dir / "img"

    # 打包文件
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 写入 Markdown 文件，放在 zip 根目录
        zipf.write(md_path, arcname=md_path.name)
        
        # 写入 img 目录下的所有文件
        if img_dir.exists() and img_dir.is_dir():
            for root, _, files in os.walk(img_dir):
                for file in files:
                    file_path = Path(root) / file
                    # 计算在 zip 中的相对路径，确保在 img/ 目录下
                    rel_path = file_path.relative_to(parent_dir)
                    zipf.write(file_path, arcname=str(rel_path))
                    
    print(f"已成功打包至: {zip_path}")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  裁剪图片: python extract_utils.py crop <图片路径> <输出路径> <left> <top> <right> <bottom>")
        print("  打包ZIP:  python extract_utils.py zip <Markdown路径> [ZIP输出路径]")
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == "crop":
        if len(sys.argv) < 8:
            print("错误: 缺少裁剪参数。格式: python extract_utils.py crop <图片路径> <输出路径> <left> <top> <right> <bottom>")
            sys.exit(1)
        img_path = sys.argv[2]
        out_path = sys.argv[3]
        try:
            coords = [float(x) for x in sys.argv[4:8]]
        except ValueError:
            print("错误: 坐标必须为数字", file=sys.stderr)
            sys.exit(1)
        
        crop_image(img_path, out_path, *coords)

    elif action == "zip":
        if len(sys.argv) < 3:
            print("错误: 缺少参数。格式: python extract_utils.py zip <Markdown路径> [ZIP输出路径]")
            sys.exit(1)
        md_path = sys.argv[2]
        zip_path = sys.argv[3] if len(sys.argv) > 3 else None
        package_zip(md_path, zip_path)
    else:
        print(f"错误: 未知操作 '{action}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
