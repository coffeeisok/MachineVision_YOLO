"""测试 PaddleOCR 3.x 返回格式"""
import cv2
import glob
from paddleocr import PaddleOCR

ocr = PaddleOCR()

# 找一张训练集图片
imgs = glob.glob("dataset/images/train/*.jpg")
if not imgs:
    print("❌ 找不到图片")
    exit(1)

img = cv2.imread(imgs[0])
print(f"测试图片: {imgs[0]}, shape={img.shape}")

r = ocr.ocr(img)

print(f"\n返回类型: {type(r)}")
print(f"返回内容: {r}")

if isinstance(r, list) and len(r) > 0:
    print(f"\nr[0] 类型: {type(r[0])}")
    if r[0] is not None:
        print(f"r[0] 内容: {r[0]}")
        print(f"r[0] 元素数: {len(r[0])}")
        if len(r[0]) > 0:
            print(f"r[0][0] 类型: {type(r[0][0])}")
            print(f"r[0][0] 内容: {r[0][0]}")
elif isinstance(r, dict):
    print(f"\ndict keys: {r.keys()}")
    for k, v in r.items():
        print(f"  {k}: {type(v)} = {v}")
