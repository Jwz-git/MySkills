#!/usr/bin/env python3
"""
图片智能裁剪脚本 - 用于 img2md skill
当图片过长时，自动检测空白区域进行裁剪，避免切到文字。
支持自适应阈值，对深色背景、低对比度图片也能正确检测文字区域。
"""

import sys
import numpy as np
from PIL import Image
from pathlib import Path


def _to_grayscale(image_array):
    """将图片转为灰度 numpy 数组"""
    if len(image_array.shape) == 3:
        # 使用加权平均（接近人眼感知），比简单 mean 更准确
        if image_array.shape[2] == 4:
            # RGBA → 去掉 alpha 通道
            image_array = image_array[:, :, :3]
        gray = np.dot(image_array[..., :3].astype(np.float32), [0.299, 0.587, 0.114]).astype(np.uint8)
    else:
        gray = image_array
    return gray


def _adaptive_threshold(gray, num_bins=100):
    """
    自适应计算行活跃度阈值。
    对于高对比度图片（如白底黑字），文字区域与空白区域差异大，阈值可以较高；
    对于低对比度图片（如深色背景），差异小，需要更低的阈值。
    """
    # 计算行间差异
    row_diff = np.abs(np.diff(gray.astype(np.float32), axis=0))
    row_activity = np.mean(row_diff, axis=1)

    # 使用直方图分析找到合适的阈值
    hist, bin_edges = np.histogram(row_activity, bins=num_bins)
    # 找到非零活跃度的中位数作为基准
    active_values = row_activity[row_activity > 0]
    if len(active_values) == 0:
        return 10  # 极端退化情况

    median_activity = np.median(active_values)
    # 阈值设为中位数的 20%，这样能适应不同对比度
    threshold = max(median_activity * 0.2, 2)
    return threshold


def detect_text_regions(image_array, row_threshold=None):
    """
    检测图片中包含文字的区域（自适应阈值版本）

    Args:
        image_array: 图片的 numpy 数组
        row_threshold: 判断一行是否包含内容的阈值（None 则自动计算）

    Returns:
        np.ndarray: 布尔数组，True 表示该行包含内容
    """
    gray = _to_grayscale(image_array)

    # 计算每一行的像素变化程度（文字区域变化较大）
    row_diff = np.abs(np.diff(gray.astype(np.float32), axis=0))
    row_activity = np.mean(row_diff, axis=1)

    # 自适应阈值
    if row_threshold is None:
        row_threshold = _adaptive_threshold(gray)

    # 判断哪些行包含内容
    text_rows = row_activity > row_threshold

    return text_rows


def find_safe_split_points(image_array, target_height=1000, overlap=150,
                           margin=30, min_gap=50):
    """
    寻找安全的裁剪点（避开文字区域）

    Args:
        image_array: 图片 numpy 数组
        target_height: 每个片段的目标高度
        overlap: 片段间重叠像素
        margin: 裁剪线距离文字的安全边距
        min_gap: 被认为是"空白区域"的最小连续行数

    Returns:
        list: 安全的裁剪位置列表（每个片段的结束 y 坐标）
    """
    height = image_array.shape[0]
    text_rows = detect_text_regions(image_array)

    split_points = []
    current_pos = target_height

    while current_pos < height - 100:  # 保留底部至少100像素
        # 在目标位置附近寻找最佳裁剪点
        search_start = max(current_pos - 200, margin)
        search_end = min(current_pos + 200, height - margin)

        best_split = None
        best_gap_size = 0

        # 寻找最大的空白区域
        i = search_start
        while i < search_end:
            if not text_rows[i]:  # 当前行没有文字
                # 计算这个空白区域有多大
                gap_start = i
                while i < search_end and not text_rows[i]:
                    i += 1
                gap_end = i
                gap_size = gap_end - gap_start

                # 如果空白区域足够大，记录中心点作为候选裁剪点
                if gap_size >= min_gap and gap_size > best_gap_size:
                    best_gap_size = gap_size
                    best_split = gap_start + gap_size // 2
            else:
                i += 1

        # 如果找到了合适的裁剪点
        if best_split and best_split > (split_points[-1] if split_points else 0) + 300:
            split_points.append(best_split)
            current_pos = best_split + target_height - overlap
        else:
            # 没找到合适的空白区域，强制在目标位置裁剪（但避开明显的文字）
            forced_split = current_pos
            # 稍微调整以避免切到文字
            for offset in range(0, 100, 5):
                if forced_split + offset < height - margin:
                    if not text_rows[forced_split + offset]:
                        forced_split += offset
                        break
                if forced_split - offset > (split_points[-1] if split_points else 0) + margin:
                    if not text_rows[forced_split - offset]:
                        forced_split -= offset
                        break

            split_points.append(forced_split)
            current_pos = forced_split + target_height - overlap

    return split_points


def split_image(input_path, output_dir=None, max_height=1000, overlap=150, height_threshold=1500):
    """
    将长图片裁剪为多个片段

    Args:
        input_path: 输入图片路径
        output_dir: 输出目录（默认为图片所在目录）
        max_height: 每个片段的最大高度
        overlap: 片段间重叠像素数
        height_threshold: 高度阈值，超过此值才裁剪

    Returns:
        list: 生成的片段文件路径列表
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"图片不存在: {input_path}")

    # 打开图片
    img = Image.open(input_path)
    width, height = img.size

    # 如果图片不够长，直接返回原图
    if height <= height_threshold:
        return [str(input_path)]

    # 确定输出目录
    if output_dir is None:
        output_dir = input_path.parent / f"{input_path.stem}_split"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 转换为 numpy 数组进行分析
    img_array = np.array(img)

    # 寻找安全的裁剪点
    split_points = find_safe_split_points(img_array, target_height=max_height, overlap=overlap)

    if not split_points:
        print("未找到合适的裁剪点，返回原图", file=sys.stderr)
        return [str(input_path)]

    print(
        f"图片高度: {height}px，将在以下位置裁剪: {split_points}",
        file=sys.stderr,
    )

    # 执行裁剪
    segments = []
    start_y = 0

    for i, end_y in enumerate(split_points):
        # 裁剪片段（包含重叠区域）
        segment = img.crop((0, start_y, width, min(end_y + overlap, height)))

        output_path = output_dir / f"{input_path.stem}_part{i+1:02d}.png"
        segment.save(output_path, "PNG")
        segments.append(str(output_path))

        print(
            f"片段 {i+1}: y={start_y} 到 {min(end_y + overlap, height)}，保存至 {output_path}",
            file=sys.stderr,
        )

        start_y = end_y

    # 最后一个片段
    if start_y < height:
        segment = img.crop((0, start_y, width, height))
        output_path = output_dir / f"{input_path.stem}_part{len(split_points)+1:02d}.png"
        segment.save(output_path, "PNG")
        segments.append(str(output_path))
        print(
            f"片段 {len(split_points)+1}: y={start_y} 到 {height}，保存至 {output_path}",
            file=sys.stderr,
        )

    print(f"共生成 {len(segments)} 个片段", file=sys.stderr)
    return segments


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python split_image.py <图片路径> [输出目录] [最大高度] [重叠像素]")
        print("示例: python split_image.py document.png ./output 1000 150")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    max_height = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    overlap = int(sys.argv[4]) if len(sys.argv) > 4 else 150

    try:
        segments = split_image(input_path, output_dir, max_height, overlap)
        print("\n生成的文件:")
        for seg in segments:
            print(f"  - {seg}")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
