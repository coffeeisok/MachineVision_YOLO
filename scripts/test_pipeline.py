"""全面测试车牌识别各环节"""
import sys, os, cv2, glob, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ultralytics import YOLO
from ocr.plate_ocr import PlateRecognizer
from color.plate_color import classify_plate_color

ocr = PlateRecognizer()
plate_model = YOLO("models/plate_best.pt")

# ============ 测试1: PaddleOCR 在 CCPD 图片上的识别 ============
print("=" * 60)
print("测试1: PaddleOCR 识别 CCPD 图片 (10张采样)")
print("=" * 60)
imgs = glob.glob("dataset/images/train/*.jpg")
samples = random.sample(imgs, min(10, len(imgs)))
ok = 0
for p in samples:
    img = cv2.imread(p)
    text = ocr.recognize(img)
    color = classify_plate_color(img)
    status = "✓" if text else "✗"
    print(f"  {status} {os.path.basename(p)[:40]}")
    if text:
        print(f"    → {text} | {color}")
        ok += 1
print(f"  结果: {ok}/{len(samples)} 识别成功")

# ============ 测试2: plate_best.pt 对 CCPD 图片的检测 ============
print()
print("=" * 60)
print("测试2: plate_best.pt 检测 CCPD 图片 (10张采样)")
print("=" * 60)
ok2 = 0
for p in samples:
    img = cv2.imread(p)
    results = plate_model(img, device=0, verbose=False)[0]
    if results.boxes is not None and len(results.boxes) > 0:
        ok2 += 1
print(f"  结果: {ok2}/{len(samples)} 检测到车牌")
print("  说明: CCPD 图片就是车牌本身, 检测不到属正常")

# ============ 测试3: 不同颜色车牌识别 ============
print()
print("=" * 60)
print("测试3: 车牌颜色分类")
print("=" * 60)
test_colors = {
    "蓝色": 0, "绿色": 0, "黄色": 0, "其他": 0
}
for p in random.sample(imgs, min(100, len(imgs))):
    img = cv2.imread(p)
    c = classify_plate_color(img)
    test_colors[c] += 1
for k, v in test_colors.items():
    print(f"  {k}: {v} 张")

# ============ 测试4: 视频多帧抽检 ============
print()
print("=" * 60)
print("测试4: 视频抽帧 + 完整流程")
print("=" * 60)
cap = cv2.VideoCapture("traffic.mp4")
total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
car_model = YOLO("yolo11n.pt")
test_frames = [1000, 3000, 5000, 7000, 9000]
found_plates = 0

for frame_n in test_frames:
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_n)
    ret, frame = cap.read()
    if not ret:
        continue
    results = car_model(frame, device=0, verbose=False)[0]
    vehicles = [b for b in (results.boxes or []) if int(b.cls[0]) in [2, 5, 7]]
    plates = 0
    for box in vehicles:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        crop = frame[y1:y2, x1:x2]
        text = ocr.recognize(crop)
        if text:
            plates += 1
            found_plates += 1
    print(f"  帧 {frame_n}: {len(vehicles)}辆车, {plates}个识别到车牌")
cap.release()
print(f"  总计: {found_plates} 个车牌")

# ============ 测试5: OCR 置信度分布 ============
print()
print("=" * 60)
print("测试5: PaddleOCR 置信度分布 (50张 CCPD)")
print("=" * 60)
confs = []
import numpy as np
from paddleocr import PaddleOCR
raw_ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
for p in random.sample(imgs, min(50, len(imgs))):
    img = cv2.imread(p)
    try:
        r = raw_ocr.ocr(img, cls=True)
        if r and r[0]:
            for line in r[0]:
                item = line[1]
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    confs.append(float(item[1]))
    except:
        pass
if confs:
    print(f"  平均置信度: {np.mean(confs):.3f}")
    print(f"  最低置信度: {np.min(confs):.3f}")
    print(f"  最高置信度: {np.max(confs):.3f}")
    print(f"  <0.5 的: {sum(1 for c in confs if c < 0.5)}/{len(confs)}")

print()
print("=" * 60)
print("总结")
print("=" * 60)
print("测试1-2: OCR 本身在 CCPD 上是否正常")
print("测试3: 颜色分类分布")
print("测试4: 在视频上车牌检出率")
print("测试5: OCR 置信度水平 (帮助判断 conf 阈值)")
