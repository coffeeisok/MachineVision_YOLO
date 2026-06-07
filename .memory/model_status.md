# model_status.md — 模型状态

> 版本：v3.1 | 更新：2026-06-07 01:10 (北京时间)

**快速概览**：5 个模型(车辆/跟踪/车牌/OCR/颜色) | 车牌自训练 mAP=0.981 | OCR 必须 CPU | 颜色纯规则

---

## 模型清单

| 模型 | 文件 | 大小 | 来源 | 设备 | 状态 |
|------|------|------|------|------|------|
| 车辆检测+分类 | yolov8m.pt | 50MB | Ultralytics COCO 预训练 | GPU | ✅ 生产 |
| 车辆跟踪 | YOLO 内置 ByteTrack | - | ultralytics | GPU | ✅ 生产 |
| **车牌检测** | **runs/detect/train-9/weights/best.pt** | **50MB** | **自己训练 CCPD2019** | **GPU** | **✅ 生产** |
| 车牌 OCR | PaddleOCR PP-OCRv4 | - | 百度通用中文模型 | **CPU** | ✅ 生产 |
| 车牌颜色 | 无 (纯规则 HSV) | - | - | CPU | ✅ 生产 |

---

## 各模型详情

### 1. 车辆检测+分类 (yolov8m.pt)
- COCO 预训练，分类 car(2)/motorcycle(3)/bus(5)/truck(7)
- 输入：全帧 4096×2160
- 推理参数：`conf=0.25`, `half=True`, `device=cuda`
- 跟踪：`.track(persist=True, tracker="bytestrack.yaml")`

### 2. 车牌检测 ([train-9](training_log.md) best.pt) — ⭐ 自训练
- 基础模型：yolov8m.pt (25.9M)
- 训练数据：CCPD2019 20k 采样 (17k train / 3k val)
- 单类别：plate (class_id=0)
- 输入：车辆 crop 区域
- 推理参数：`conf=0.25`, `imgsz=480`, `half=True`
- 训练详情见 [training_log.md](training_log.md) §成功训练详情
- **绝对路径**（云端）：`/root/autodl-tmp/traffic_project/runs/detect/train-9/weights/best.pt`

### 3. PaddleOCR (PP-OCRv4)
- 百度通用中文识别模型
- **必须 CPU 模式**：`use_gpu=False`，否则 segfault（详见 [known_issues.md](known_issues.md) §技术黑名单 #2）
- 图像增强管线：灰度 → 2x 超分(INTER_CUBIC) → 对比度拉伸(alpha=1.5, beta=20) → 高斯去噪(3x3)
- 文本清洗：正则过滤，保留 31 省份简称 + A-Z + 0-9
- 配置：`use_angle_cls=True`, `lang="ch"`, `show_log=False`

### 4. HSV 颜色分类
- 纯规则，无需训练
- 蓝色：H[100-140] S[80-255] V[80-255]
- 绿色：H[35-90] S[50-255] V[50-255]
- 黄色：H[15-35] S[80-255] V[80-255]
- 最低阈值：8% 像素占比
- 输出：蓝/绿/黄/其他

---

## 训练超参数（固定，不要改）

```yaml
model:     yolov8m.pt
data:      data.yaml          # path: dataset, 单类 0: plate
epochs:    50
batch:     64
imgsz:     640
device:    0
cache:     ram
workers:   4
amp:       True
optimizer: auto               # MuSGD
```

## 推理参数（推荐）

```bash
--vehicle-model  yolov8m.pt
--plate-model    runs/detect/train-9/weights/best.pt
--device         cuda
--no-gpu-ocr                     # 必须！否则 segfault
--half                           # FP16，速度翻倍
--plate-imgsz    480             # 比 640 快 1.8x
--conf           0.25
--plate-conf     0.25
--line-y         0               # auto = 画面 60% 位置
--retry          10              # OCR 重试间隔(帧)
--output         results/output_v3.mp4
```

## 模型文件位置

| 文件 | 本地路径 | 云端路径 |
|------|---------|---------|
| yolov8m.pt | `MachineVision_finalTest/yolov8m.pt` | `traffic_project/yolov8m.pt` |
| best.pt | 无 (不跟踪, 不入 git) | `traffic_project/runs/detect/train-9/weights/best.pt` |
| yolo11n.pt | `MachineVision_finalTest/yolo11n.pt` | 仅 AMP 检查用，勿训练 |
| yolo11s.pt | `MachineVision_finalTest/yolo11s.pt` | 同上 |
| yolo26n.pt | `MachineVision_finalTest/yolo26n.pt` | 同上 |

---

## 相关文档

- [training_log.md](training_log.md) — 训练记录 + 结果
- [known_issues.md](known_issues.md) — 参数约束（batch≤64, workers≤4）
- [architecture.md](architecture.md) — 推理管线中每个模型的位置
- [handoff.md](handoff.md) §16 — 完整训练/推理参数
