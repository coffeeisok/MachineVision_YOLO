"""
src/plate_ocr.py — 车牌 OCR 识别模块 (v3.0)
基于 PaddleOCR PP-OCRv4，参考项目 2/ 已验证的成功模式。

架构极简：
  enhance() → PaddleOCR.ocr() → clean_plate() → (text, confidence)
"""
import re
import numpy as np
import cv2
from paddleocr import PaddleOCR


class PlateOCR:
    """车牌文字识别器 — 单例 PaddleOCR，避免重复加载"""

    def __init__(self, gpu: bool = True):
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang="ch",
            show_log=False,
            use_gpu=gpu,
        )

    # ---- 文本清洗 ------------------------------------------------
    @staticmethod
    def clean_plate(text: str) -> str:
        """
        去掉空格、转大写，只保留车牌合法字符：
        31 省份简称 + 大写字母 + 数字
        """
        text = text.replace(" ", "").upper()
        return re.sub(
            r"[^A-Z0-9"
            r"京沪粤津渝苏浙鲁川鄂湘皖赣闽贵云桂琼黑吉辽陕甘青豫冀晋蒙藏宁新"
            r"]",
            "",
            text,
        )

    # ---- 图像增强 ------------------------------------------------
    @staticmethod
    def enhance(img: np.ndarray) -> np.ndarray:
        """
        灰度 → 2x 超分 → 对比度拉伸 → 高斯去噪
        参考项目已验证：对监控远景小车牌有效
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=20)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        return gray

    # ---- 核心接口 ------------------------------------------------
    def recognize(self, plate_img: np.ndarray) -> tuple[str, float]:
        """
        识别车牌图像中的文字。

        Args:
            plate_img: BGR 车牌裁剪图

        Returns:
            (车牌号, 平均置信度) — 失败返回 ("Unknown", 0.0)
        """
        if plate_img is None or plate_img.size == 0:
            return "Unknown", 0.0

        try:
            enhanced = self.enhance(plate_img)
            result = self.ocr.ocr(enhanced, cls=True)

            text = ""
            scores = []

            if result and result[0]:
                for line in result[0]:
                    text += line[1][0]
                    scores.append(line[1][1])

            conf = float(np.mean(scores)) if scores else 0.0
            cleaned = self.clean_plate(text)

            if not cleaned:
                return "Unknown", 0.0

            return cleaned, conf

        except Exception:
            return "Unknown", 0.0
