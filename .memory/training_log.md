# training_log.md — 训练记录

> 版本：v3.1 | 更新：2026-06-07 01:10 (北京时间)

**快速概览**：train-1~6(全废yolo11n) → train-7(OOM) → train-8(太慢) → train-9(✅mAP=0.981)

---

## 训练尝试汇总

| # | 模型 | batch | 其他 | 结果 |
|---|------|-------|------|------|
| train-1~3 | yolo11n | 32 | - | ❌ 空权重，一次没跑完 |
| train-4 | yolo11n | 32 | 100 epoch | ❌ 22 epoch 崩，mAP50-95=0.14 |
| train-5 | yolo11n | 64 | - | ❌ 5 epoch 崩，mAP50-95=0.28 |
| train-6 | yolo11n | 64 | 100 epoch | ❌ 跑完 100 epoch，mAP50-95=0.10 |
| train-7 | yolov8m | 128 | - | ❌ CUDA OOM，自动降 batch 但 DataLoader 崩溃 |
| train-8 | yolov8m | 64 | cache=disk, workers=8 | ❌ 太慢，磁盘 I/O 瓶颈 |
| **train-9** | **yolov8m** | **64** | **cache=ram, workers=4, amp** | **✅ mAP50=0.995, mAP50-95=0.981** |

---

## ✅ 成功训练详情 (train-9)

### 配置
```
基础模型:  yolov8m.pt (25.9M 参数)
Epochs:    50
Batch:     64
Imgsz:     640
Optimizer: MuSGD (auto)
AMP:       True
Cache:     ram
Workers:   4
设备:      RTX 3090 24GB
数据集:    CCPD2019 20k 采样 (17k train / 3k val)
类别:      单类 plate (class_id=0)
```

### 结果
```
mAP50:     0.995
mAP50-95:  0.981
best.pt:   50 MB
训练耗时:  ~2.5 小时
每 epoch:  ~3.5 分钟
```

### 产出位置
```
云端: /root/autodl-tmp/traffic_project/runs/detect/train-9/weights/best.pt
本地: 未同步（50MB，不入 git）
```

### vs 旧版
```
              v2.x(train-6)    v3.1(train-9)
基础模型        yolo11n           yolov8m
参数量          2.6M              25.9M
mAP50           0.995             0.995
mAP50-95        0.10              0.981
提升            -                 约 10x
```

---

## 关键教训

1. **模型不能太小**：yolo11n (2.6M) 不足以学习车牌小目标 → 必须 ≥ yolov8m (25.9M)。参数差 10 倍，mAP 差 10 倍。（详见 [decisions.md](decisions.md) §决策2）
2. **batch 不能太大**：128 OOM，64 稳定。显存占用 ~22.7G/24G。（详见 [known_issues.md](known_issues.md) §技术黑名单 #3）
3. **cache=ram 必须限制 workers**：>4 触发 DataLoader 共享内存崩溃（详见 [known_issues.md](known_issues.md) §技术黑名单 #4）
4. **50 epoch 足够**：不需要 100，mAP50-95 在 epoch 35 后趋于平稳
5. **参考已验证方案**：`2/` 目录里的 YOLOv8m + CCPD 跑通了，不要自作聪明换模型（详见 [decisions.md](decisions.md) §决策2）

---

## 相关文档

- [session_log.md](session_log.md) — 每次训练尝试的完整上下文
- [known_issues.md](known_issues.md) — 训练黑名单
- [model_status.md](model_status.md) — 模型清单 + 训练/推理参数
- [decisions.md](decisions.md) — 为什么选 yolov8m 而不是 yolo11n
