# known_issues.md — 已知问题与黑名单

> 版本：v3.2 | 更新：2026-06-07 15:30 (北京时间)

**快速概览**：11 条禁止操作 / 2 个未解决 bug / 稳定参数速查表

---

## 🚫 技术黑名单 — 绝对不要重试

| # | 禁止做什么 | 原因 | 后果 | 状态 |
|---|-----------|------|------|------|
| 1 | 用 yolo11n 训练车牌检测 | 2.6M 参数太小，无法学习车牌小目标 | mAP50-95 ≤ 0.28（6 次训练全废） | 永久禁止 |
| 2 | PaddleOCR GPU 模式 | CUDA 12.8 与 PaddlePaddle 2.6.2 GPU 算子接口不兼容（[session_log.md](session_log.md) §阶段3） | `Segmentation fault` at `FusedConv2dAddActKernel` | 已知，无修复计划 |
| 3 | batch > 64 | RTX 3090 24GB，yolov8m + amp 跑 128 刚好爆显存 | CUDA OOM | 永久限制 |
| 4 | workers > 4 (cache=ram) | 多 worker 共享内存争用 + ram 缓存占满内存 | `DataLoader worker exited unexpectedly` | 永久限制 |
| 5 | cache=disk | AutoDL 数据盘 NVMe 非为大量随机小文件读取优化 | 训练慢 3x（磁盘 I/O 瓶颈） | 能 ram 就 ram |
| 6 | warpPerspective / IOU 匹配架构 | 过度设计，v2.x 已证明复杂不带来效果提升 | 代码复杂，车牌识别大量错误（车身文字被当成车牌） | 永久废弃 |
| 7 | 用 YOLOv11（任何尺寸） | 无证据优于 YOLOv8，v2.x 全部训练失败；参考项目 YOLOv8m 已验证成功 | 训练全部失败 | 永久禁止 |

## 🚫 流程黑名单

| # | 禁止 | 原因 | 状态 |
|---|------|------|------|
| 8 | push 代码前不问用户 | [CLAUDE.md](../CLAUDE.md) + [project_rules.md](project_rules.md) 明确规定 | 永久规则 |
| 9 | pip install 不加 `--no-deps` | numpy 会被自动升级到 2.x，引发 Paddle/PaddleOCR/cv2 连环崩溃 | 永久规则 |
| 10 | 在 /tmp 放工程文件 | AutoDL 临时目录重启丢失、不稳定、易冲突（[session_log.md](session_log.md) §阶段2/4） | 永久规则 |
| 11 | 不用 screen 跑长任务 | SSH 断开丢进度，v2.x 多次发生 | 永久规则 |

---

## 🟡 已知未解决问题

| # | 问题 | 优先级 | 根因 | 状态 |
|---|------|--------|------|------|
| 1 | 省份汉字偶漏识别（如 `BFX528` 少了省份） | 中 | 通用 PaddleOCR PP-OCRv4 域偏移，未在车牌数据上微调 | 待 OCR 微调解决 |
| 2 | 同一车牌可能断跟踪（不同 track_id） | 低 | ByteTrack 在高位俯拍视角下偶发 ID switch | 已知，可接受 |
| 3 | Pillow `load_default()` 字体不可缩放 | 🔴高 | 找不到中文字体时回退到 10px 位图，无论 font_size 多大都极小 | 已修复 — FONT_PATHS 加入 wqy-zenhei.ttc |

---

## 稳定参数速查

### 训练
```
yolov8m.pt | batch=64 | workers=4 | cache=ram | amp=True | imgsz=640 | epochs=50
```

### 推理
```
--device cuda --no-gpu-ocr --half --plate-imgsz=480 --conf=0.25 --line-y=0 --retry=10
```

### OCR 微调
```
batch_size_per_card=32 | num_workers=2 | epochs=60
```

---

## 排查经验

### 训练崩了怎么查？
1. 先看是不是 OOM (batch 太大) → batch=128 必崩，64 稳定
2. 再看是不是 DataLoader (workers 太多) → cache=ram 时 workers≤4
3. mAP 低 → 检查是不是用了 nano 模型
4. loss 不收敛 → 检查数据路径、标签是否正确

### 推理崩了怎么查？
1. segfault → PaddleOCR GPU 模式，换 `--no-gpu-ocr`
2. 车牌识别全是 Unknown → PaddleOCR 初始化失败或图片为空
3. 汉字全显示 ???? → 字体文件找不到，回退默认字体
4. 文字极小如像素点（4K 下看不清）→ Pillow `load_default()` 回退到不可缩放的 10px 位图。解决：确保 FONT_PATHS 中有 wqy-zenhei.ttc

---

## 🟠 域偏移分析（CCPD → 监控视频）

> 来源：docs/车牌识别算法分析.md，合并于 2026-06-07

### 问题本质

```
CCPD2019 训练数据          实际监控视频
   近景 (>200px)      →     远景 (20-60px)
   正面/小角度         →     高位俯拍
   高清 (720×1160)     →     低分辨率整帧中的小区域
```

这是典型的**训练-部署域偏移**（Domain Shift），不是算法缺陷。

### 改进方向

| # | 方向 | 说明 |
|---|------|------|
| 1 | 多尺度检测 | 对车辆区域做 2x 上采样后再做车牌检测 |
| 2 | 域适应微调 | 用监控视频抽帧标注少量车牌，在 CCPD 预训练上微调 |
| 3 | 超分辨率预处理 | 对车牌候选区域做轻量 SR 后再 OCR |
| 4 | 降低 conf 阈值 | 配合更严格的文本格式过滤（格式先验可过滤 90% 车身文字误检） |

### 实战教训

- **不要依赖单一方案**。YOLO 检测快但泛化差，DB 检测通用但慢，级联架构取长补短
- **近景训练 ≠ 远景可用**。CCPD2019 验证 mAP 0.98，不代表实际场景 0.98
- **格式先验很关键**。中国车牌固定格式（省份+字母+5~6位），利用此先验可过滤大量误检
- **颜色分类用规则比训练好**。HSV 阈值法零成本、可解释、易调试
- **OCR 是全链路瓶颈**。检测 1ms + OCR 5ms = 每车 6ms，10 路并发需要 60ms/帧
- **PaddleOCR 版本敏感**。2.7→3.6 API 全变，生产环境必须锁定版本

---

## 相关文档

- [session_log.md](session_log.md) — 完整失败记录 + 报错分析
- [training_log.md](training_log.md) — 9 次训练尝试详情
- [project_rules.md](project_rules.md) — AI 协作约束 + 禁止事项
- [model_status.md](model_status.md) — 稳定参数速查
