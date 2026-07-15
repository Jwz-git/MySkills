#!/usr/bin/env python3
"""
图片裁剪与打包工具 - 用于 img2md skill
提供两个主要功能：
1. crop: 从输入图片中裁剪出指定区域，并保存到指定位置（通常是 img/ 目录）。
   坐标系通过 --coords 显式指定，避免小于 1000 的像素值被误判为归一化坐标。
2. zip: 将 Markdown 文件和同级的 img/ 目录整体打包为 ZIP 文件。
"""

import os
import sys
import zipfile
from pathlib import Path


def _load_pillow():
    """加载 Pillow；缺失时给出可执行提示，但不擅自修改环境。"""
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "缺少 Pillow。请在当前 Python 环境中运行: "
            f"{sys.executable} -m pip install Pillow"
        ) from exc
    return Image


def _to_pixels(coords, width, height, coordinate_system):
    """将指定坐标系中的矩形转换为像素坐标。"""
    left, top, right, bottom = coords
    limits = {
        "pixels": None,
        "unit": 1.0,
        "thousand": 1000.0,
    }
    if coordinate_system not in limits:
        raise ValueError(
            f"未知坐标系 {coordinate_system!r}；可选值: pixels, unit, thousand"
        )

    scale = limits[coordinate_system]
    if scale is None:
        return tuple(int(value) for value in coords)

    if not all(0.0 <= value <= scale for value in coords):
        raise ValueError(
            f"{coordinate_system} 坐标必须全部位于 0 到 {scale:g} 之间"
        )

    return (
        int(left / scale * width),
        int(top / scale * height),
        int(right / scale * width),
        int(bottom / scale * height),
    )


def crop_image(
    image_path,
    output_path,
    left,
    top,
    right,
    bottom,
    coordinate_system="pixels",
):
    """
    裁剪图片指定区域并保存
    """
    Image = _load_pillow()

    image_path = Path(image_path).resolve()
    output_path = Path(output_path).resolve()

    if not image_path.is_file():
        raise FileNotFoundError(f"输入图片不存在或不是文件: {image_path}")

    # 自动创建输出目录
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as img:
        width, height = img.size
        left_px, top_px, right_px, bottom_px = _to_pixels(
            (left, top, right, bottom), width, height, coordinate_system
        )

        # 像素坐标允许越界输入，并裁剪到图像边界。
        left_px = max(0, min(left_px, width))
        top_px = max(0, min(top_px, height))
        right_px = max(0, min(right_px, width))
        bottom_px = max(0, min(bottom_px, height))

        if left_px >= right_px or top_px >= bottom_px:
            raise ValueError(
                f"无效的裁剪范围 ({left_px}, {top_px}, {right_px}, {bottom_px})"
            )

        cropped = img.crop((left_px, top_px, right_px, bottom_px))
        # 输出固定为 PNG，避免 OCR 素材再次产生有损压缩。
        cropped.save(output_path, "PNG")
    print(f"已成功裁剪区域并保存至: {output_path}")


def package_zip(md_path, zip_path=None):
    """
    将 Markdown 文件和同级的 img/ 目录打包为 ZIP
    """
    md_path = Path(md_path).resolve()
    if not md_path.is_file():
        raise FileNotFoundError(f"Markdown 文件不存在或不是文件: {md_path}")

    if zip_path is None:
        zip_path = md_path.with_suffix(".zip")
    else:
        zip_path = Path(zip_path).resolve()
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    parent_dir = md_path.parent
    img_dir = parent_dir / "img"

    # 打包文件
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
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
        print("  裁剪图片: python3 extract_utils.py crop <图片路径> <输出路径> <left> <top> <right> <bottom> [--coords pixels|unit|thousand]")
        print("  打包ZIP:  python3 extract_utils.py zip <Markdown路径> [ZIP输出路径]")
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == "crop":
        if len(sys.argv) not in (8, 10):
            print("错误: 参数格式为 python3 extract_utils.py crop <图片路径> <输出路径> <left> <top> <right> <bottom> [--coords pixels|unit|thousand]")
            sys.exit(1)
        img_path = sys.argv[2]
        out_path = sys.argv[3]
        try:
            coords = [float(x) for x in sys.argv[4:8]]
        except ValueError:
            print("错误: 坐标必须为数字", file=sys.stderr)
            sys.exit(1)

        coordinate_system = "pixels"
        if len(sys.argv) > 8:
            if len(sys.argv) != 10 or sys.argv[8] != "--coords":
                print(
                    "错误: 可选参数格式为 --coords pixels|unit|thousand",
                    file=sys.stderr,
                )
                sys.exit(1)
            coordinate_system = sys.argv[9]

        try:
            crop_image(
                img_path,
                out_path,
                *coords,
                coordinate_system=coordinate_system,
            )
        except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            sys.exit(1)

    elif action == "zip":
        if len(sys.argv) not in (3, 4):
            print("错误: 参数格式为 python3 extract_utils.py zip <Markdown路径> [ZIP输出路径]")
            sys.exit(1)
        md_path = sys.argv[2]
        zip_path = sys.argv[3] if len(sys.argv) > 3 else None
        try:
            package_zip(md_path, zip_path)
        except (FileNotFoundError, OSError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"错误: 未知操作 '{action}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
