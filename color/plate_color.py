"""
color/plate_color.py
基于 HSV 颜色空间的车牌底色分类.

融合参考项目策略:
  - HSV 范围采用工程常用配置
  - 最低占比阈值 8% (参考项目)
  - 返回最佳匹配 (而非首个匹配)
"""
import cv2
import numpy as np

# HSV 颜色范围 (参考项目工程常用配置)
COLOR_RANGES: dict[str, tuple[list[int], list[int]]] = {
    "蓝色": ([100, 80, 80], [140, 255, 255]),
    "绿色": ([35, 50, 50],  [90, 255, 255]),
    "黄色": ([15, 80, 80],  [35, 255, 255]),
}

MIN_RATIO = 0.08  # 参考项目: 8%


class PlateColorRecognizer:
    """车牌颜色识别器"""

    def recognize(self, plate_img: np.ndarray) -> tuple[str, float]:
        """
        Args:
            plate_img: 车牌 BGR 图像

        Returns:
            (颜色名称, 像素占比)
        """
        if plate_img is None or plate_img.size == 0:
            return "其他", 0.0

        hsv = cv2.cvtColor(plate_img, cv2.COLOR_BGR2HSV)
        best_color = "其他"
        best_ratio = 0.0

        for color_name, (lower, upper) in COLOR_RANGES.items():
            mask = cv2.inRange(hsv, np.array(lower, np.uint8),
                               np.array(upper, np.uint8))
            ratio = float(np.sum(mask > 0) / mask.size)
            if ratio > best_ratio:
                best_ratio = ratio
                best_color = color_name

        if best_ratio < MIN_RATIO:
            return "其他", best_ratio

        return best_color, best_ratio


# 模块级便捷函数 (兼容旧接口)
_default = None


def classify_plate_color(plate_img: np.ndarray) -> str:
    """便捷函数: 返回颜色名称"""
    global _default
    if _default is None:
        _default = PlateColorRecognizer()
    color, _ = _default.recognize(plate_img)
    return color
