# decisions.md — 关键决策记录

> 本次项目所有关键决策及其原因。按时间顺序排列。

---

## 决策 1：推倒 v2.x 全部重来

**时间**：2026-06-06 会话开始

**背景**：v2.x 代码膨胀至 9 模块 ~1500 行，YOLOv11 nano 训练 6 次全部失败，依赖版本混乱，越改越差。

**决策**：全部推倒，基于参考项目 `2/` 成功模式重建 v3.0。

**为什么**：
- v2.x 架构过度设计（全帧双检测+IOU 匹配+warpPerspective）复杂且效果差
- 参考项目 `2/` 用更简单的方案跑通了（车辆 crop 内检测车牌）
- 继续修修补补只会更糟

**放弃的方案**：在 v2.x 基础上迭代修复

---

## 决策 2：YOLOv8 替代 YOLOv11

**时间**：2026-06-06

**背景**：v2.x 用 YOLOv11 nano 训练，mAP50-95 仅 0.10。参考项目用 YOLOv8m 成功。

**决策**：用 YOLOv8m (25.9M 参数) 训练车牌检测。

**为什么**：
- 参考项目已验证 YOLOv8m 在 CCPD 上好用
- YOLOv8m 比 YOLOv11n 大 10 倍参数
- 不折腾，用验证过的方案

**放弃的方案**：YOLOv11（任何尺寸）

---

## 决策 3：架构极简化（3 模块 vs 9 模块）

**时间**：2026-06-06

**决策**：
- 删除手动 ByteTrack 封装 → YOLO 内置 `.track()`
- 删除手动 counter → supervision LineZone
- 删除 warpPerspective 透视矫正 → 简单 enhance()
- 删除 IOU 匹配 → 车辆 crop 内检测车牌
- OCR、颜色、推理三合一

**为什么**：
- 参考项目证明简单方案有效
- 每多一个模块就多一个出错点
- v2.x 的复杂性没有带来效果提升

**放弃的方案**：保留 IOU 匹配、透视矫正等复杂逻辑

---

## 决策 4：依赖全锁定，numpy 死锁 1.26.4

**时间**：2026-06-06

**背景**：v2.x 因 pip 自由安装导致 numpy 被升级到 2.x，引发 Paddle/PaddleOCR/cv2 连环崩溃。

**决策**：
- requirements.txt 所有包 pin 死版本
- numpy==1.26.4 绝对禁止升级
- 所有后续 pip install 加 `--no-deps`

**为什么**：numpy 2.x ABI 与 PaddlePaddle 不兼容，一升就全体崩溃。这是 v2.x 最大的环境坑。

---

## 决策 5：PaddleOCR 永远用 CPU 模式

**时间**：2026-06-07

**背景**：推理时 PaddleOCR GPU 模式 segfault (CUDA 12.8 不兼容)。

**决策**：`--no-gpu-ocr` 永远开启，OCR 只在 CPU 跑。

**为什么**：
- CUDA 12.8 + PaddlePaddle 2.6.2 GPU segfault 是已知问题
- OCR 只是识别几个车牌小图，CPU 足够快（~10ms/张）
- 完全不影响总推理速度（瓶颈在 YOLO 不在 OCR）

**放弃的方案**：降级 CUDA、重装 PaddlePaddle（风险大不值得）

---

## 决策 6：训练用 cache=ram + workers=4

**时间**：2026-06-06

**背景**：workers=14 + cache=ram 导致 DataLoader 共享内存爆仓；cache=disk 导致训练太慢。

**决策**：cache=ram, workers=4。

**为什么**：
- 90GB 物理内存，train(12GB) + val(2GB) + model + overhead 轻松装下
- workers=4 是 DataLoader 稳定上限
- 比 disk 快 3 倍

**放弃的方案**：workers=14 (崩溃), workers=8 (偶发崩溃), cache=disk (太慢)

---

## 决策 7：batch=64 不追求 128

**时间**：2026-06-06

**背景**：batch=128 在 RTX 3090 上 OOM（yolov8m + amp 吃满 24GB）。

**决策**：batch=64。

**为什么**：
- 128 刚好爆显存（YOLO 自动降级机制触发但不稳定）
- 64 稳如狗，显存占用 ~22.7G/24G
- 50 epoch 足够收敛到 mAP50-95=0.981

**放弃的方案**：batch=128（OOM）, batch=96（没试但 128 都爆了不值得试）

---

## 决策 8：IN/OUT 方向定义

**时间**：2026-06-07

**背景**：视频中绝大部分车都是驶离（尾朝摄像机），用户希望这样记为 OUT。

**决策**：
- IN = 驶近（车头面向摄像机，画面中向下运动）
- OUT = 驶离（车尾面向摄像机，画面中向上运动）
- 通过反转 LineZone 方向实现

**为什么**：与直觉一致。`LINE_START=(width, line_y), LINE_END=(0, line_y)` → 向下运动=IN。

---

## 决策 9：FP16 半精度推理

**时间**：2026-06-07

**决策**：推理时默认推荐 `--half`。

**为什么**：
- 速度翻倍（~2x throughput）
- 精度损失可忽略（车牌检测和车辆检测都不需要 FP32 精度）
- RTX 3090 原生支持 FP16 硬件加速

---

## 决策 10：跳过远处车辆的车牌检测

**时间**：2026-06-07

**决策**：`vy2 < height * 0.3`（车辆底边在画面顶部 30%）的车辆跳过车牌检测。

**为什么**：
- 远处的车牌照占画面极小（<20px），OCR 读不了
- 跳过这些车减少无效 PaddleOCR 调用
- 不影响车流量统计（越线判断只看越线行为）

---

## 决策 11：GitHub 版本管理 + 云端不联网

**时间**：2026-06-06

**决策**：
- 代码在 GitHub (`git@github.com:coffeeisok/MachineVision_YOLO.git`) 管理
- 云端通过 FileZilla/scp 同步代码，不与 GitHub 通信
- push 前必须征求用户同意

**为什么**：
- 版本管理方便回溯
- 云端到 GitHub 网速极慢（11 KB/s）
- 用户明确要求云端禁止连接 GitHub

---

## 决策 12：修复 Pillow 字体回退 Bug — 渲染字号失效根因

**时间**：2026-06-07 02:00

**背景**：推理输出视频中所有中文标签极小（形同像素点），无论 `font_size` 设为 36、48、180 都无效。排查发现：AutoDL 镜像的 `/usr/share/fonts/` 下没有代码 FONT_PATHS 中列出的 NotoSansCJK 字体，导致 `load_font()` 回退到 `ImageFont.load_default()`。Pillow 的默认字体是固定 ~10px 的**位图字体，不支持缩放**，传入任何 font_size 都返回同样的 10px 文字。在 4K (4096×2160) 画面上，10px 文字形同像素点。

**决策**：
1. FONT_PATHS 加入 `wqy-zenhei.ttc`（文泉驿正黑，AutoDL/Ubuntu 最常见预装字体）
2. `load_font()` 兼容 Pillow ≥10.1 的 `load_default(size=size)` 语法
3. `draw_labels_pil()` 新增 `bg_color` 参数，在文字下方画不透明背景矩形提高对比度
4. 字号回归合理值：方框标签 32，面板 42，计数线 text_scale=1.2

**为什么**：
- 之前所有字号调整都是白费的，因为字体根本没加载成功
- 需要在 FONT_PATHS 中加入目标环境**实际存在的**字体路径
- 背景色块大幅提高 4K 复杂背景下的文字可读性

**放弃的方案**：盲目调大 font_size（180、200），因为根因不是字号太小而是字体没加载

---

## 决策 13：draw_labels_pil 支持背景色块

---

## 性能优化思路

| 优化 | 方式 | 效果 |
|------|------|------|
| YOLO FP16 | `half=True` | ~2x |
| 车牌模型降分辨率 | imgsz=640 → 480 | ~1.8x |
| 跳过远处车 | 画面 30% 以上不检测 | 减少无效计算 |
| cache=ram | 训练时内存缓存 | 消除磁盘 I/O |

## 精度优化思路

| 优化 | 方式 | 当前状态 |
|------|------|---------|
| 大模型 | yolo11n → yolov8m | ✅ 10x 提升 |
| 数据增强 | albumentations (auto) | ✅ 默认开启 |
| OCR 微调 | CCPD 车牌数据特训 | 🔜 备用方案 |

---

## 排查过程：训练为什么失败？

1. 检查 `runs/detect/train/args.yaml` → 发现全部用 `yolo11n.pt`（nano 模型）
2. 检查 `runs/detect/train-4/results.csv` → mAP50-95 仅 0.14
3. 检查 `runs/detect/train-6/results.csv` → mAP50-95 仅 0.10
4. 检查 `models/plate_best.pt` 大小 → 207MB（不是自己训的，从参考项目拷的）
5. **结论**：6 次训练全部用错了模型大小，没有一个能用的产出

## 排查过程：推理为什么 segfault？

1. PaddleOCR GPU 模式 → `Segmentation fault` at `FusedConv2dAddActKernel`
2. 试 `--no-gpu-ocr` → 正常
3. 查 CUDA 版本 → 12.8（对 PaddlePaddle 2.6 来说太新）
4. **结论**：CUDA 12.8 + PaddlePaddle GPU 模式不兼容，CPU 模式就够了

---

## 相关文档

- [session_log.md](session_log.md) — 每次决策的执行上下文
- [training_log.md](training_log.md) — 训练相关决策的验证结果
- [architecture.md](architecture.md) — 架构相关决策的落地结构
- [project_rules.md](project_rules.md) — 决策衍生的长期规则
