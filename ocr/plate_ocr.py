"""
ocr/plate_ocr.py
车牌识别模块 — 融合参考项目策略 + 自研透视矫正.

OCR流程:
  1. enhance(): 灰度 → 2x上采样 → 对比度提升 → 高斯模糊
  2. PaddleOCR 识别
  3. clean_plate(): 过滤非车牌字符
  4. 透视矫正 (perspective_correct): 梯形 → 矩形 (可选)
"""
import cv2
import re
import numpy as np
from paddleocr import PaddleOCR


class PlateRecognizer:
    """车牌文字识别 + 透视矫正"""

    # 合法车牌字符集
    VALID_CHARS = (
        "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"
        "京沪粤津渝苏浙鲁川鄂湘皖赣闽贵云桂琼黑吉辽陕甘青豫冀晋蒙藏宁新"
    )

    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='ch',
            show_log=False,
            use_gpu=True
        )

    # ==================== 文本清洗 (参考项目策略) ====================

    @classmethod
    def clean_plate(cls, text: str) -> str:
        """
        清洗 OCR 输出: 去空格 → 大写 → 只保留合法车牌字符.
        比正则格式校验更宽容、更准确.
        """
        text = text.replace(" ", "").upper()
        return re.sub(rf'[^{cls.VALID_CHARS}]', '', text)

    # ==================== 图像增强 (参考项目策略) ====================

    @staticmethod
    def enhance(img: np.ndarray) -> np.ndarray:
        """
        灰度 → 2x 超分 → 对比度提升 → 高斯滤波.
        简单但极其有效.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=20)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        return gray

    # ==================== 透视矫正 (自研) ====================

    @staticmethod
    def perspective_correct(plate_img: np.ndarray) -> np.ndarray | None:
        """
        warpPerspective 梯形车牌 → 矩形车牌.
        失败返回 None.
        """
        if plate_img is None or plate_img.size == 0:
            return None
        try:
            h, w = plate_img.shape[:2]
            if h < 15 or w < 50:
                return None

            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 200)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            dilated = cv2.dilate(edges, kernel, iterations=1)

            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)

            for cnt in sorted(contours, key=cv2.contourArea, reverse=True):
                area = cv2.contourArea(cnt)
                if area < (h * w * 0.10):
                    continue
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
                if len(approx) != 4:
                    continue

                pts = approx.reshape(4, 2).astype(np.float32)
                s = pts.sum(axis=1)
                tl, br = pts[np.argmin(s)], pts[np.argmax(s)]
                diff = np.diff(pts, axis=1).ravel()
                tr, bl = pts[np.argmin(diff)], pts[np.argmax(diff)]

                src_pts = np.array([tl, tr, br, bl], dtype=np.float32)
                plate_w = max(int(np.linalg.norm(tl - tr)),
                              int(np.linalg.norm(bl - br)), 100)
                plate_h = max(int(np.linalg.norm(tl - bl)),
                              int(np.linalg.norm(tr - br)), 32)
                dst_pts = np.array([
                    [0, 0], [plate_w - 1, 0],
                    [plate_w - 1, plate_h - 1], [0, plate_h - 1]
                ], dtype=np.float32)

                M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                return cv2.warpPerspective(plate_img, M, (plate_w, plate_h))

            return None
        except Exception:
            return None

    # ==================== 核心识别接口 ====================

    def recognize(self, plate_img: np.ndarray) -> tuple[str, float]:
        """
        车牌 OCR.

        Args:
            plate_img: 车牌 BGR 图像

        Returns:
            (清洗后的车牌文本, 平均置信度)
        """
        if plate_img is None or plate_img.size == 0:
            return "", 0.0

        try:
            # 1. 图像增强
            enhanced = self.enhance(plate_img)

            # 2. PaddleOCR
            result = self.ocr.ocr(enhanced, cls=True)

            text = ""
            scores = []
            if result and result[0]:
                for line in result[0]:
                    text += line[1][0]
                    scores.append(line[1][1])

            if not scores:
                return "", 0.0

            conf = float(np.mean(scores))

            # 3. 文本清洗
            cleaned = self.clean_plate(text)
            if not cleaned or len(cleaned) < 5:
                return "", 0.0

            return cleaned, conf

        except Exception:
            return "", 0.0
