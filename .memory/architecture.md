# architecture.md — 系统架构与项目结构

> 最后更新：2026-06-07

---

## 一、推理管线（核心数据流）

```
视频帧 (4096×2160, 12 FPS)
  │
  ├─→ YOLOv8m.track(classes=[car,bus,truck,motorcycle], half=True)     [GPU]
  │     │
  │     ├─→ supervision LineZone 越线计数              [CPU]
  │     │     ├─ IN  (驶近) = 越过线且向下运动
  │     │     └─ OUT (驶离) = 越过线且向上运动
  │     │
  │     └─→ 每辆车 crop
  │           │
  │           ├─ 跳过 vy2 < height*0.3 的远处车
  │           │
  │           └─→ YOLOv8m(plate, imgsz=480, half=True) [GPU]
  │                 │
  │                 ├─→ PaddleOCR PP-OCRv4             [CPU]
  │                 │     ├─ enhance(): 灰度→2x超分→对比度→高斯去噪
  │                 │     └─ clean_plate(): 正则过滤非车牌字符
  │                 │
  │                 └─→ HSV 颜色分类                    [CPU]
  │                       ├─ 蓝色: H[100-140] S[80-255] V[80-255]
  │                       ├─ 绿色: H[35-90]  S[50-255] V[50-255]
  │                       ├─ 黄色: H[15-35]  S[80-255] V[80-255]
  │                       └─ 其他: 都不够 8% 像素占比
  │
  └─→ PIL 中文渲染 → MP4 输出
       ├─ 车辆标签: "车牌号 | 颜色 | 车型" (48px 大字)
       └─ 统计面板: Traffic Flow / Plates / IN / OUT / 分车型 (44px)
```

---

## 二、模型来源

| 模型 | 文件 | 大小 | 来源 | 设备 |
|------|------|------|------|------|
| 车辆检测+分类 (car/bus/truck/motorcycle) | yolov8m.pt | 50MB | COCO 预训练 | GPU |
| 车辆跟踪 (ByteTrack) | YOLO 内置 | - | ultralytics | GPU |
| **车牌检测 (plate)** | **train-9 best.pt** | **50MB** | **自己训练 CCPD2019** | GPU |
| 车牌文字识别 | PaddleOCR PP-OCRv4 | - | 百度通用中文模型 | CPU |
| 车牌颜色分类 (蓝/绿/黄/其他) | 无 (纯规则) | - | HSV | CPU |

---

## 三、模块结构

### src/ — 核心推理代码（v3.1，3 个文件）

| 文件 | 行数 | 职责 |
|------|------|------|
| `src/infer.py` | ~310 | 主推理管线：双 YOLO + PaddleOCR + HSV + LineZone 全流程 |
| `src/plate_ocr.py` | ~80 | PaddleOCR 封装：单例模式，enhance() + clean_plate() + recognize() |
| `src/plate_color.py` | ~55 | HSV 颜色分类：蓝/绿/黄/其他 四分类，8% 最低阈值 |

### scripts/ — 一次性数据工具

| 文件 | 作用 |
|------|------|
| `scripts/convert_ccpd.py` | CCPD2019 文件名解析 → YOLO .txt 格式，带进度条 + ETA |
| `scripts/split_dataset.py` | 训练/验证集随机分割 (85/15) |

### 配置文件

| 文件 | 内容 |
|------|------|
| `data.yaml` | YOLO 训练配置：`path: dataset`，单类 `0: plate` |
| `requirements.txt` | 所有依赖全锁定版本，numpy==1.26.4 死锁 |
| `.gitignore` | 排除 .mp4 .zip .pt dataset/ CCPD2019/ ccpd/ runs/ results/ models/ 2/ |

---

## 四、完整目录树

```
MachineVision_finalTest/                    # ★ 项目根目录
│
├── CLAUDE.md                               # AI Agent 全局约束
├── README.md                               # 人类阅读的项目说明
│
├── .memory/                                # ★ AI 长期记忆
│   ├── current_state.md                    #   项目大脑：进度、阻塞
│   ├── next_tasks.md                       #   优先级待办
│   ├── known_issues.md                     #   黑名单 + Bug
│   ├── training_log.md                     #   训练尝试记录
│   ├── model_status.md                     #   模型路径/指标/参数
│   ├── architecture.md                     #   本文件
│   ├── decisions.md                        #   关键决策记录
│   ├── project_rules.md                    #   AI 协作规范 + 元规则
│   ├── session_log.md                      #   会话与实验记录
│   └── handoff.md                          #   项目交接文档
│
├── src/                                    # v3.1 核心代码（3 个文件）
│   ├── __init__.py
│   ├── infer.py                            #   主推理管线 (~310行) ⭐
│   ├── plate_ocr.py                        #   PaddleOCR 封装 (~80行)
│   └── plate_color.py                      #   HSV 颜色分类 (~55行)
│
├── scripts/                                # 数据工具脚本
│   ├── convert_ccpd.py                     #   CCPD2019 → YOLO 格式
│   └── split_dataset.py                    #   训练/验证集划分
│
├── docs/                                   # 文档
│   └── 车牌识别算法分析.md
│
├── 2/                                      # 参考项目 (成功跑通, 不动它)
│   ├── traffic_analysis_complete.py        #   参考主管线
│   ├── traffic_counter.py                  #   参考计数管线
│   ├── ocr/plate_recognition.py            #   参考 OCR 模块
│   ├── models/color_recognition.py         #   参考颜色模块
│   └── models/best.pt                      #   参考车牌模型
│
├── data.yaml                               # YOLO 训练配置
├── requirements.txt                        # Python 依赖
├── .gitignore                              # Git 排除规则
│
├── traffic.mp4                             # 测试视频 (452MB, 🚫 git)
│
├── CCPD2019/                               # 原始数据集 (9.6GB, 🚫 git)
│   └── CCPD2019/
│       ├── ccpd_base/                      #   主线数据 (~100k 张)
│       ├── ccpd_challenge/                 #   挑战子集
│       ├── ccpd_db/                        #   光照变化
│       ├── ccpd_fn/                        #   远近变化
│       ├── ccpd_rotate/                    #   旋转
│       ├── ccpd_tilt/                      #   倾斜
│       └── ccpd_weather/                   #   天气变化
│
├── ccpd/                                   # OCR 微调数据 (🚫 git)
│   └── ccpd_base_plate/                    #   78,896 纯车牌裁剪图
│
├── dataset/                                # YOLO 训练数据 (🚫 git)
│   ├── ccpd_yolo/                          #   全量转换 (121,431张)
│   │   ├── images/
│   │   └── labels/
│   ├── images/train/                       #   训练集 (17,000张)
│   ├── images/val/                         #   验证集 (3,000张)
│   └── labels/train/ + val/
│
├── models/                                 # 模型权重 (🚫 git)
│   └── plate_best.pt                       #   旧版 207MB (不可用)
│
├── results/                                # 推理输出 (🚫 git)
│   ├── output.mp4                          #   v1 未优化版 (2.6GB)
│   └── output_v3.mp4                       #   v3 优化版 (待生成)
│
└── runs/                                   # 训练记录 (🚫 git)
    └── detect/
        ├── train/ ~ train-8/               #   失败训练
        └── train-9/                        #   ★ 唯一成功
            ├── weights/best.pt             #     ★ 最终模型 (50MB)
            ├── weights/last.pt
            └── results.csv
```

---

## 五、目录用途速查

| 目录 | 用途 | git | 变动频率 |
|------|------|-----|---------|
| `src/` | v3.1 核心推理代码 | ✅ | 高 |
| `scripts/` | 一次性数据工具 | ✅ | 低 |
| `.memory/` | AI 长期记忆 | ✅ | 中 |
| `docs/` | 算法分析文档 | ✅ | 低 |
| `2/` | 参考项目 | 🚫 | 不动 |
| `CCPD2019/` | 原始训练数据 | 🚫 | 不动 |
| `ccpd/` | OCR 微调数据 | 🚫 | 不动 |
| `dataset/` | YOLO 格式训练数据 | 🚫 | 重新生成 |
| `models/` | 模型权重 | 🚫 | 训练后更新 |
| `results/` | 推理输出视频 | 🚫 | 每次推理 |
| `runs/` | 训练记录 | 🚫 | 每次训练 |

---

## 六、技术栈

```
Python 3.10 + conda
YOLOv8m (车辆检测 + 内置 ByteTrack 跟踪)
YOLOv8m (车牌检测, CCPD2019 训练, mAP50-95=0.981)
PaddleOCR (PP-OCRv4, CPU 推理)
OpenCV + supervision (越线计数 + HSV 颜色分类)
PIL (中文车牌标签渲染)
```

---

## 七、数据集情况

### 训练数据

| 项目 | 值 |
|------|-----|
| 来源 | CCPD2019（7.2GB 原始 → 9.6GB 解压） |
| 全量子集 | ccpd_base/challenge/db/fn/rotate/tilt/weather |
| 全量图片 | 121,431 张 |
| 采样训练 | 20,000 张 (85/15) |
| 训练集 | 17,000 张 |
| 验证集 | 3,000 张 |
| 标注格式 | YOLO .txt (class_id xc yc w h) |
| 类别 | 单类：plate (class_id=0) |

### OCR 微调数据（备用）

| 项目 | 值 |
|------|-----|
| 来源 | ccpd_base_plate 子集 |
| 数量 | 78,896 张纯车牌裁剪图 |
| 大小 | 1.3GB (ccpd.zip) |

### 测试视频

| 项目 | 值 |
|------|-----|
| 文件 | traffic.mp4 |
| 分辨率 | 4096×2160 (DCI 4K) |
| 帧率 | 12 FPS |
| 时长 | 15 分钟, 10,813 帧 |
| 大小 | 452 MB |
| 视角 | 高位俯拍，单向车流（大部分车辆驶离） |

---

## 八、云端环境

| 项目 | 值 |
|------|-----|
| GPU | RTX 3090 24GB ×1 |
| CPU | 14 vCPU Intel Xeon Gold 6330 @ 2.00GHz |
| 内存 | 90 GB |
| 系统盘 | 30 GB |
| 数据盘 | 50 GB |
| CUDA | 12.8 |
| PyTorch | 2.11.0+cu128 |
| Conda env | `traffic` (Python 3.10.20) |
| 云端路径 | `/root/autodl-tmp/traffic_project/` |

---

## 九、v2.x 已删除的文件（v3.1 清理）

```
deploy/infer.py                     → src/infer.py 替代
ocr/plate_ocr.py                    → src/plate_ocr.py 替代
color/plate_color.py                → src/plate_color.py 替代
tracking/tracker.py                 → YOLO 内置 ByteTrack
tracking/counter.py                 → supervision LineZone
train/train.py                      → YOLO CLI (yolo detect train)
check_dependencies.py               → requirements.txt 锁定
scripts/extract_frames.py           → 不需要
scripts/prepare_ocr_data.py         → 暂时不用
scripts/test_ocr.py                 → 不需要
scripts/test_pipeline.py            → 不需要
```

---

## 相关文档

- [model_status.md](model_status.md) — 每个模型在管线中的位置与参数
- [decisions.md](decisions.md) — 架构简化的决策过程（决策 3/5/9/10）
- [handoff.md](handoff.md) §6 — 技术架构详解
- [project_rules.md](project_rules.md) §7 — 文件组织规则
