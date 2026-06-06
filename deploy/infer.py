"""
deploy/infer.py
主推理管线 v2.8 — 全帧双检测 + 缓存重试架构

融合策略:
  自研: 全帧车牌检测 (imgsz=1920) + IOU匹配 + 透视矫正
  参考: 车牌缓存+重试(每10帧) + clean_plate清洗 + enhance增强

使用方法:
    python deploy/infer.py --video traffic.mp4
"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import cv2
import numpy as np
import argparse
import time
from collections import defaultdict

from ultralytics import YOLO
import supervision as sv

from tracking.tracker import ByteTrackWrapper
from tracking.counter import LineCounter
from ocr.plate_ocr import PlateRecognizer
from color.plate_color import PlateColorRecognizer


def main(video_path: str, vehicle_model_path: str, plate_model_path: str,
         line_y: int = 0, output_path: str = "results/output.mp4",
         skip_frames: int = 1, imgsz: int = 1280,
         plate_imgsz: int = 1920, plate_every: int = 1,
         vehicle_conf: float = 0.35):

    # ==================== 初始化 ====================
    print(f"车辆检测模型: {vehicle_model_path} (imgsz={imgsz})")
    vehicle_model = YOLO(vehicle_model_path)

    print(f"车牌检测模型: {plate_model_path} (imgsz={plate_imgsz})")
    plate_model = YOLO(plate_model_path)

    ocr = PlateRecognizer()
    color_rec = PlateColorRecognizer()

    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if line_y <= 0:
        line_y = int(h * 0.53)

    tracker = ByteTrackWrapper(frame_rate=fps)
    counter = LineCounter(line_y=line_y, min_cross_dist=20)

    print(f"视频: {w}x{h}, {fps} FPS, {total_frames} 帧")
    print(f"横截线: y={line_y} | 车辆 imgsz={imgsz} | 车牌 imgsz={plate_imgsz}")
    print(f"车牌检测间隔: 每 {plate_every} 帧")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_thickness=1, text_scale=0.5)

    VEHICLE_CLASS_IDS = [2, 5, 7]
    CLASS_NAMES = {2: "Car", 5: "Bus", 7: "Truck"}

    frame_count = 0
    processed_count = 0

    # 缓存机制 (参考项目策略)
    plate_cache: dict[int, dict] = {}          # track_id → {text, color, last_check}
    track_best_plate: dict[int, np.ndarray] = {}
    track_best_area: dict[int, float] = {}
    plate_recognized: set[int] = set()         # 已确认识别成功的 track
    active_ids_prev: set[int] = set()

    t_start = time.time()
    print("\n开始推理...\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1

        if frame_count % skip_frames != 0:
            continue
        processed_count += 1

        # ==================== 1. 车辆检测 + 跟踪 ====================
        vehicle_results = vehicle_model(frame, device=0, imgsz=imgsz, verbose=False)[0]
        detections = sv.Detections.from_ultralytics(vehicle_results)

        if len(detections) > 0:
            mask_cls = np.isin(detections.class_id, VEHICLE_CLASS_IDS)
            mask_conf = detections.confidence >= vehicle_conf
            detections = detections[mask_cls & mask_conf]

        detections = tracker.update(detections)

        current_frame_ids = set(int(tid) for tid in detections.tracker_id) if len(detections.tracker_id) > 0 else set()

        # ==================== 2. 全帧车牌检测 + IOU匹配 ====================
        if frame_count % plate_every == 0:
            plate_results = plate_model(frame, device=0, imgsz=plate_imgsz,
                                        conf=0.25, verbose=False)[0]

            if plate_results.boxes is not None and len(plate_results.boxes) > 0:
                for box in plate_results.boxes:
                    px1, py1, px2, py2 = map(int, box.xyxy[0])
                    pcx = (px1 + px2) / 2.0
                    pcy = (py1 + py2) / 2.0
                    plate_area = (px2 - px1) * (py2 - py1)
                    if plate_area < 200:
                        continue

                    for i, vbox in enumerate(detections.xyxy):
                        vx1, vy1, vx2, vy2 = vbox
                        if vx1 <= pcx <= vx2 and vy1 <= pcy <= vy2:
                            tid = int(detections.tracker_id[i])
                            if tid not in track_best_area or plate_area > track_best_area[tid]:
                                crop_x1 = max(0, px1 - 5)
                                crop_y1 = max(0, py1 - 5)
                                crop_x2 = min(w, px2 + 5)
                                crop_y2 = min(h, py2 + 5)
                                track_best_plate[tid] = frame[crop_y1:crop_y2, crop_x1:crop_x2].copy()
                                track_best_area[tid] = plate_area
                            break

        # ==================== 3. 缓存策略: 首次/重试 OCR ====================
        for tid in current_frame_ids:
            # 已确认识别 → 跳过
            if tid in plate_recognized:
                continue

            # 缓存命中 → 检查是否需要重试
            if tid in plate_cache and plate_cache[tid]["text"]:
                last_check = plate_cache[tid].get("last_check", 0)
                if frame_count - last_check >= 10:
                    # 每10帧尝试重试 (有时后续帧车牌更清晰)
                    pass  # 继续往下走
                else:
                    continue  # 还没到重试时间

            # 有最佳车牌帧 → 尝试 OCR
            if tid in track_best_plate:
                plate_crop = track_best_plate[tid]

                # 4a. 透视矫正
                corrected = PlateRecognizer.perspective_correct(plate_crop)
                target = corrected if corrected is not None else plate_crop

                # 4b. OCR
                p_text, p_conf = ocr.recognize(target)

                # 4c. 如果矫正后失败，用原图重试
                if not p_text and corrected is not None:
                    p_text, p_conf = ocr.recognize(plate_crop)

                # 4d. 颜色
                p_color, _ = color_rec.recognize(plate_crop)

                if p_text:
                    plate_recognized.add(tid)
                    plate_cache[tid] = {"text": p_text, "color": p_color,
                                        "conf": p_conf, "last_check": frame_count}
                    print(f"  [Frame {frame_count}] ID={tid} "
                          f"车牌={p_text} 颜色={p_color} 置信度={p_conf:.2%}")
                else:
                    # 标记已尝试但失败，等下次重试
                    plate_cache[tid] = {"text": "", "color": "其他",
                                        "conf": 0.0, "last_check": frame_count}

        # ==================== 4. 越线计数 ====================
        crossed_ids = counter.update(detections)

        for track_id, direction in crossed_ids:
            if track_id in plate_cache and plate_cache[track_id]["text"]:
                cached = plate_cache[track_id]
                print(f"  ✅ ID={track_id} 越线({direction}) "
                      f"车牌={cached['text']} 颜色={cached['color']}")
            else:
                print(f"  ⚠️  ID={track_id} 越线({direction}) 车牌=未识别")

        # ==================== 5. 清理离线 track ====================
        for prev_id in list(active_ids_prev):
            if prev_id not in current_frame_ids:
                if prev_id in track_best_plate:
                    del track_best_plate[prev_id]
                if prev_id in track_best_area:
                    del track_best_area[prev_id]
        active_ids_prev = current_frame_ids

        # ==================== 6. 渲染 ====================
        labels = []
        for i, track_id in enumerate(detections.tracker_id):
            tid = int(track_id)
            direction = counter.get_direction(tid)
            cls_id = int(detections.class_id[i]) if len(detections.class_id) > i else -1
            conf = float(detections.confidence[i]) if len(detections.confidence) > i else 0.0
            vtype = CLASS_NAMES.get(cls_id, "")
            label = f"ID:{tid} {vtype} ({conf:.1%})"
            if direction:
                label += f" {direction}"
            if tid in plate_cache and plate_cache[tid]["text"]:
                label += f"\n{plate_cache[tid]['text']} {plate_cache[tid]['color']}"
            elif tid in plate_cache:
                label += "\n..."
            labels.append(label)

        annotated = box_annotator.annotate(frame.copy(), detections)
        annotated = label_annotator.annotate(annotated, detections, labels)
        cv2.line(annotated, (0, line_y), (w, line_y), (0, 255, 0), 2)

        panel_x, panel_y = 10, 30
        cv2.putText(annotated, f"Forward : {counter.forward_count}",
                    (panel_x, panel_y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 0), 2)
        cv2.putText(annotated, f"Backward: {counter.backward_count}",
                    (panel_x, panel_y + 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 0, 255), 2)
        cv2.putText(annotated, f"Total   : {counter.total_count}",
                    (panel_x, panel_y + 60), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 0), 2)
        cv2.putText(annotated, f"Frame: {frame_count}/{total_frames}",
                    (panel_x, panel_y + 90), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (200, 200, 200), 1)

        out.write(annotated)

        if processed_count % 100 == 0:
            n_recognized = len(plate_recognized)
            print(f"  进度: {frame_count}/{total_frames} 帧 | "
                  f"正向={counter.forward_count} 反向={counter.backward_count} | "
                  f"识别={n_recognized}")

    # ==================== 结束 ====================
    cap.release()
    out.release()
    cv2.destroyAllWindows()

    elapsed = time.time() - t_start
    n_plate = len(plate_recognized)
    n_total = counter.total_count
    print(f"\n{'='*50}")
    print(f"推理完成!")
    print(f"正向车流: {counter.forward_count}")
    print(f"反向车流: {counter.backward_count}")
    print(f"总计:     {n_total}")
    print(f"识别车牌: {n_plate}/{n_total} "
          f"({n_plate/n_total*100:.1f}%)" if n_total > 0 else "")
    print(f"用时:     {elapsed:.0f} 秒 ({elapsed/60:.1f} 分钟)")
    print(f"结果视频: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="交通监控智能分析 v2.8")
    parser.add_argument("--video", default=os.path.join(PROJECT_ROOT, "traffic.mp4"))
    parser.add_argument("--vehicle_model", default="yolo11s.pt")
    parser.add_argument("--plate_model",
                        default=os.path.join(PROJECT_ROOT, "models", "plate_best.pt"))
    parser.add_argument("--line_y", type=int, default=0)
    parser.add_argument("--output",
                        default=os.path.join(PROJECT_ROOT, "results", "output.mp4"))
    parser.add_argument("--skip", type=int, default=1)
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--plate_imgsz", type=int, default=1920)
    parser.add_argument("--plate_every", type=int, default=1)
    parser.add_argument("--vehicle_conf", type=float, default=0.35)
    args = parser.parse_args()

    main(args.video, args.vehicle_model, args.plate_model,
         args.line_y, args.output, args.skip, args.imgsz,
         args.plate_imgsz, args.plate_every, args.vehicle_conf)
