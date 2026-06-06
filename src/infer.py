#!/usr/bin/env python3
"""
src/infer.py — 交通监控智能分析主推理管线 (v3.0)

极简架构（参考项目 2/ 已验证）：

    视频帧
      │
      ├─→ YOLOv8m.track(classes=[car,bus,truck,motorcycle])
      │         │
      │         ├─→ supervision LineZone 越线计数
      │         └─→ 每辆车 crop → plate_model → PaddleOCR + 颜色
      │
      └─→ 渲染标签 + 统计面板 → 输出视频

用法:
    python src/infer.py --video traffic.mp4
    python src/infer.py --video traffic.mp4 --device cpu --no-gpu-ocr
"""

import os
import sys
import argparse
import cv2
import numpy as np
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

import supervision as sv
from ultralytics import YOLO

# 将项目根目录加入 path，方便导入同目录模块
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.plate_ocr import PlateOCR
from src.plate_color import PlateColor


# ============================================================
# 配置
# ============================================================

# 车辆类别 (COCO)
VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck
CLASS_NAMES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

# 中文字体路径（AutoDL 常见位置；找不到则回退默认）
FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",  # macOS
]


def load_font(size: int = 40) -> ImageFont.FreeTypeFont:
    """加载中文字体，找不到则用默认字体"""
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def draw_labels_pil(img: np.ndarray, labels: list[tuple]) -> np.ndarray:
    """
    用 PIL 批量绘制中文标签（避免 OpenCV putText 中文乱码）。
    labels: [(position, text, color), ...]
    """
    if not labels:
        return img
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = load_font(36)
    for item in labels:
        pos, text, color = item if len(item) == 3 else (item[0], item[1], (0, 255, 0))
        draw.text(pos, text, font=font, fill=color)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


# ============================================================
# 主推理管线
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="交通监控智能分析 v3.0")
    parser.add_argument("--video", default="traffic.mp4", help="输入视频路径")
    parser.add_argument("--vehicle-model", default="yolov8m.pt", help="车辆检测模型")
    parser.add_argument("--plate-model", default="models/plate_best.pt", help="车牌检测模型")
    parser.add_argument("--output", default="results/output.mp4", help="输出视频路径")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"], help="推理设备")
    parser.add_argument("--no-gpu-ocr", action="store_true", help="OCR 用 CPU")
    parser.add_argument("--conf", type=float, default=0.25, help="车辆检测置信度")
    parser.add_argument("--plate-conf", type=float, default=0.25, help="车牌检测置信度")
    parser.add_argument("--line-y", type=int, default=0, help="横截线 y (0=自动画面60%)")
    parser.add_argument("--retry", type=int, default=10, help="OCR 重试间隔(帧)")
    args = parser.parse_args()

    # --------------------------------------------------------
    # 初始化模型
    # --------------------------------------------------------
    print("=" * 60)
    print("  交通监控智能分析系统 v3.0")
    print("=" * 60)

    print(f"\n[1/4] 加载车辆检测模型: {args.vehicle_model}")
    vehicle_model = YOLO(args.vehicle_model)

    plate_model = None
    if os.path.exists(args.plate_model):
        print(f"[2/4] 加载车牌检测模型: {args.plate_model}")
        plate_model = YOLO(args.plate_model)
    else:
        print(f"[2/4] ⚠️  车牌模型不存在: {args.plate_model}，跳过车牌识别")

    use_ocr_gpu = not args.no_gpu_ocr and args.device == "cuda"
    print(f"[3/4] 初始化 PaddleOCR (GPU={use_ocr_gpu})...")
    ocr = PlateOCR(gpu=use_ocr_gpu)
    color_rec = PlateColor()

    print(f"[4/4] 打开视频: {args.video}")
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"❌ 无法打开视频: {args.video}")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 12
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # 横截线位置
    line_y = args.line_y if args.line_y > 0 else int(height * 0.60)
    LINE_START = sv.Point(0, line_y)
    LINE_END = sv.Point(width, line_y)

    # Supervision 组件
    line_zone = sv.LineZone(start=LINE_START, end=LINE_END)
    line_annotator = sv.LineZoneAnnotator(
        thickness=4, text_thickness=3, text_scale=2,
        color=sv.Color.from_hex("#FF0000"),
    )
    box_annotator = sv.BoxAnnotator(thickness=3)

    # 输出视频
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(args.output, fourcc, fps, (width, height))

    print(f"    分辨率: {width}x{height} | FPS: {fps} | 总帧: {total_frames}")
    print(f"    横截线 y={line_y} | 设备: {args.device}")
    print(f"\n{'='*60}\n")

    # --------------------------------------------------------
    # 状态机
    # --------------------------------------------------------
    plate_cache: dict[int, dict] = {}       # track_id → {text, color, last_check}
    reported: set[int] = set()              # 已上报 track_id
    id_to_class: dict[int, str] = {}        # track_id → class_name

    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        # ---- A. 车辆检测 + 跟踪 ---------------------------------
        track_results = vehicle_model.track(
            frame,
            persist=True,
            classes=VEHICLE_CLASSES,
            conf=args.conf,
            tracker="bytetrack.yaml",
            device=args.device,
            verbose=False,
        )[0]

        detections = sv.Detections.from_ultralytics(track_results)

        if track_results.boxes.id is not None:
            detections.tracker_id = track_results.boxes.id.cpu().numpy().astype(int)
        else:
            detections.tracker_id = np.array([], dtype=int)

        # ---- B. 车牌识别 ----------------------------------------
        labels_to_draw = []

        for i in range(len(detections)):
            track_id = int(detections.tracker_id[i])
            vx1, vy1, vx2, vy2 = map(int, detections.xyxy[i])
            class_name = CLASS_NAMES.get(int(detections.class_id[i]), "vehicle")

            if track_id not in id_to_class:
                id_to_class[track_id] = class_name

            p_text, p_color = "Unknown", "Unknown"

            if track_id in plate_cache:
                cached = plate_cache[track_id]
                if cached["text"] != "Unknown":
                    p_text, p_color = cached["text"], cached["color"]
                # 过期重试
                elif frame_idx - cached.get("last_check", 0) >= args.retry:
                    should_ocr = True
                else:
                    p_text, p_color = cached["text"], cached["color"]
                    should_ocr = False
            else:
                should_ocr = True

            if should_ocr and plate_model is not None:
                # 裁剪车辆区域
                pad = 15
                cx1 = max(0, vx1 - pad)
                cy1 = max(0, vy1 - pad)
                cx2 = min(width, vx2 + pad)
                cy2 = min(height, vy2 + pad)
                vehicle_crop = frame[cy1:cy2, cx1:cx2]

                if vehicle_crop.size > 0:
                    plate_results = plate_model(
                        vehicle_crop, conf=args.plate_conf, verbose=False
                    )

                    for pr in plate_results:
                        if pr.boxes is not None and len(pr.boxes) > 0:
                            px1, py1, px2, py2 = map(
                                int, pr.boxes.xyxy.cpu().numpy()[0]
                            )
                            plate_img = vehicle_crop[py1:py2, px1:px2]

                            if plate_img.size > 0:
                                p_text, conf = ocr.recognize(plate_img)
                                plate_color, _ = color_rec.classify(plate_img)
                                p_color = plate_color
                            break  # 只取第一个检测到的车牌

                plate_cache[track_id] = {
                    "text": p_text,
                    "color": p_color,
                    "last_check": frame_idx,
                }

            # 上报新车牌
            if track_id not in reported and p_text not in ("Unknown", "Error"):
                reported.add(track_id)
                print(f"  ✨ [ID:{track_id:<3}] {class_name:<5} | {p_text:<8} | {p_color}")

            # 标签
            display = f"{p_text} | {p_color}" if p_text != "Unknown" else "Scanning..."
            labels_to_draw.append(((vx1, max(10, vy1 - 50)), display, (0, 255, 0)))

        # ---- C. 越线计数 ----------------------------------------
        line_zone.trigger(detections=detections)

        # ---- D. 可视化渲染 --------------------------------------
        frame = box_annotator.annotate(scene=frame, detections=detections)

        # 统计面板 (右上角)
        stats = defaultdict(int)
        for cls in id_to_class.values():
            stats[cls] += 1
        total = len(id_to_class)

        overlay = frame.copy()
        panel_x = width - 640
        cv2.rectangle(overlay, (panel_x, 30), (width - 30, 420), (15, 15, 15), -1)
        cv2.rectangle(overlay, (panel_x, 30), (width - 30, 420), (255, 255, 255), 2)
        frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)

        RED = (255, 0, 0)
        labels_to_draw.extend([
            ((panel_x + 40, 50), "TRAFFIC STATS", RED),
            ((panel_x + 40, 100), f"Total: {total}", RED),
            ((panel_x + 40, 150), f"Cars: {stats.get('car', 0)}", RED),
            ((panel_x + 40, 200), f"Buses: {stats.get('bus', 0)}", RED),
            ((panel_x + 40, 250), f"Trucks: {stats.get('truck', 0)}", RED),
            ((panel_x + 40, 300), f"Motorcycles: {stats.get('motorcycle', 0)}", RED),
            ((panel_x + 40, 360), f"IN: {line_zone.in_count}  OUT: {line_zone.out_count}", RED),
        ])

        frame = draw_labels_pil(frame, labels_to_draw)
        frame = line_annotator.annotate(frame=frame, line_counter=line_zone)
        writer.write(frame)

        # 进度
        pct = (frame_idx / total_frames) * 100 if total_frames else 0
        print(
            f"\r  [{frame_idx}/{total_frames}] {pct:.1f}%  "
            f"online:{len(detections)}  plates:{len(reported)}  "
            f"IN:{line_zone.in_count} OUT:{line_zone.out_count}",
            end="", flush=True,
        )

    # --------------------------------------------------------
    # 结束
    # --------------------------------------------------------
    cap.release()
    writer.release()
    print(f"\n\n{'='*60}")
    print(f"  ✅ 完成！")
    print(f"  正向 (IN) : {line_zone.in_count}")
    print(f"  反向 (OUT): {line_zone.out_count}")
    print(f"  输出视频  : {args.output}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
