#!/usr/bin/env python3
"""为视觉读取准备图片，并在标准输出返回单个 JSON 对象。"""

import json
import sys
from pathlib import Path


HEIGHT_THRESHOLD = 1500
TARGET_HEIGHT = 1000
OVERLAP = 150


def _dependency_error(exc):
    missing = getattr(exc, "name", "Pillow/NumPy")
    return RuntimeError(
        f"缺少 Python 依赖 {missing}。请运行: "
        f"{sys.executable} -m pip install Pillow numpy"
    )


def _load_pillow():
    try:
        from PIL import Image
    except ImportError as exc:
        raise _dependency_error(exc) from exc
    return Image


def _load_split_image():
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from split_image import split_image
    except ImportError as exc:
        raise _dependency_error(exc) from exc
    return split_image


def get_image_info(image_path):
    """返回尺寸、格式、颜色模式和帧数。"""
    Image = _load_pillow()
    with Image.open(image_path) as img:
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
            "frame_count": getattr(img, "n_frames", 1),
            "is_animated": bool(getattr(img, "is_animated", False)),
        }


def _prepare_single(input_path, output_dir=None):
    """准备单帧图片，并返回供上层聚合的结果。"""
    info = get_image_info(input_path)
    if info["height"] <= HEIGHT_THRESHOLD:
        return {
            "needs_split": False,
            "files": [str(Path(input_path).resolve())],
            "output_dir": None,
        }

    split_image = _load_split_image()
    input_path = Path(input_path).resolve()
    split_dir = (
        Path(output_dir).resolve()
        if output_dir is not None
        else input_path.parent / f"{input_path.stem}_split"
    )
    files = split_image(
        str(input_path),
        str(split_dir),
        max_height=TARGET_HEIGHT,
        overlap=OVERLAP,
        height_threshold=HEIGHT_THRESHOLD,
    )
    return {"needs_split": len(files) > 1, "files": files, "output_dir": str(split_dir)}


def _extract_tiff_pages(input_path, output_dir):
    """把多页 TIFF 展开为稳定、可独立读取的 PNG 页面。"""
    Image = _load_pillow()
    input_path = Path(input_path).resolve()
    pages_dir = Path(output_dir).resolve()
    pages_dir.mkdir(parents=True, exist_ok=True)

    pages = []
    with Image.open(input_path) as img:
        for index in range(img.n_frames):
            img.seek(index)
            page_path = pages_dir / f"{input_path.stem}_page{index + 1:03d}.png"
            img.copy().save(page_path, "PNG")
            pages.append(page_path)
    return pages


def _extract_gif_first_frame(input_path, output_dir):
    """把动画 GIF 的第一帧固化为 PNG，避免读取工具选择其他帧。"""
    Image = _load_pillow()
    input_path = Path(input_path).resolve()
    frames_dir = Path(output_dir).resolve()
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_path = frames_dir / f"{input_path.stem}_frame001.png"
    with Image.open(input_path) as img:
        img.seek(0)
        img.copy().convert("RGBA").save(frame_path, "PNG")
    return frame_path


def prepare(input_path, output_dir=None):
    """检测帧数和尺寸，返回按阅读顺序排列的文件列表。"""
    input_path = Path(input_path).resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"图片不存在或不是文件: {input_path}")

    info = get_image_info(input_path)
    notes = []
    files_to_read = []
    generated_dirs = []
    needs_split = False

    if info["format"] == "TIFF" and info["frame_count"] > 1:
        pages_root = (
            Path(output_dir).resolve()
            if output_dir is not None
            else input_path.parent / f"{input_path.stem}_pages"
        )
        pages = _extract_tiff_pages(input_path, pages_root)
        generated_dirs.append(str(pages_root))
        notes.append(f"多页 TIFF 已按顺序展开为 {len(pages)} 页。")
        for page in pages:
            page_result = _prepare_single(page, pages_root / f"{page.stem}_split")
            files_to_read.extend(page_result["files"])
            needs_split = needs_split or page_result["needs_split"]
            if page_result["output_dir"]:
                generated_dirs.append(page_result["output_dir"])
    elif info["format"] == "GIF" and info["frame_count"] > 1:
        frames_root = (
            Path(output_dir).resolve()
            if output_dir is not None
            else input_path.parent / f"{input_path.stem}_frames"
        )
        first_frame = _extract_gif_first_frame(input_path, frames_root)
        generated_dirs.append(str(frames_root))
        single_result = _prepare_single(first_frame, frames_root / "frame001_split")
        files_to_read.extend(single_result["files"])
        needs_split = single_result["needs_split"]
        if single_result["output_dir"]:
            generated_dirs.append(single_result["output_dir"])
        notes.append(
            f"动画 GIF 共 {info['frame_count']} 帧；默认只读取第一帧。"
        )
    else:
        single_result = _prepare_single(input_path, output_dir)
        files_to_read.extend(single_result["files"])
        needs_split = single_result["needs_split"]
        if single_result["output_dir"]:
            generated_dirs.append(single_result["output_dir"])

    result = {
        "needs_split": needs_split,
        "image_info": info,
        "files_to_read": files_to_read,
        "generated_dirs": list(dict.fromkeys(generated_dirs)),
        "notes": notes,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    if len(sys.argv) not in (2, 3):
        print(
            "用法: python3 prepare_image.py <图片路径> [临时输出目录]",
            file=sys.stderr,
        )
        return 2

    try:
        prepare(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
