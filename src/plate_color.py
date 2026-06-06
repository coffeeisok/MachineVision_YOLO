"""
src/plate_color.py — 车牌颜色识别模块 (v3.0)
基于 HSV 颜色空间，纯规则，无需训练。
"""
import cv2
import numpy as np


class PlateColor:
    """车牌底色分类器 — HSV 像素占比，最佳匹配"""

    def __init__(self):
        # HSV 范围 (OpenCV: H∈[0,180], S∈[0,255], V∈[0,255])
        self.ranges = {
            "蓝色": [(100, 80, 80), (140, 255, 255)],
            "绿色": [(35, 50, 50), (90, 255, 255)],
            "黄色": [(15, 80, 80), (35, 255, 255)],
        }
        self.min_ratio = 0.08  # 最低 8% 像素占比才算

    def classify(self, plate_img: np.ndarray) -> tuple[str, float]:
        """
        识别车牌底色。

        Returns:
            ("蓝色"/"绿色"/"黄色"/"其他", 置信度/像素占比)
        """
        if plate_img is None or plate_img.size == 0:
            return "其他", 0.0

        hsv = cv2.cvtColor(plate_img, cv2.COLOR_BGR2HSV)

        best_color = "其他"
        best_score = 0.0

        for name, (lower, upper) in self.ranges.items():
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            ratio = float(np.sum(mask > 0) / mask.size)

            if ratio > best_score:
                best_score = ratio
                best_color = name

        if best_score < self.min_ratio:
            return "其他", best_score

        return best_color, best_score
