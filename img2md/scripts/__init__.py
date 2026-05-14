# img2md scripts package

"""
img2md 图片处理脚本包

公共 API:
    prepare(input_path, output_dir=None) -> dict
        预处理入口：检测图片尺寸，决定是否裁剪，返回待处理文件列表。

    split_image(input_path, output_dir=None, max_height=1000, overlap=150, height_threshold=1500) -> list
        将长图片裁剪为多个片段，返回片段文件路径列表。

    detect_text_regions(image_array, row_threshold=None) -> np.ndarray
        检测图片中包含文字的区域（自适应阈值）。
"""

from .prepare_image import prepare, get_image_info
from .split_image import split_image, detect_text_regions, find_safe_split_points

__all__ = [
    "prepare",
    "get_image_info",
    "split_image",
    "detect_text_regions",
    "find_safe_split_points",
]
