# next_tasks.md — 待办清单

> 版本：v3.1 | 更新：2026-06-07 02:20 (北京时间)

**快速概览**：P0=推理v5验证+报告+PPT / P1=用户肉眼抽查 / P2=OCR微调备用

---

## P0 — 必须完成（课程提交用）

### 1. ~~推理 v5（字体修复版）~~ 🔄 运行中
```bash
# 已启动，cloud screen infer_v5
# 预计 03:10 完成
python src/infer.py --video traffic.mp4 \
  --vehicle-model yolov8m.pt \
  --plate-model runs/detect/train-9/weights/best.pt \
  --device cuda --no-gpu-ocr --half \
  --output results/output_v5.mp4
```

### 2. 用户抽查验证 🔜
- 下载 `output_v5.mp4` 到本地
- 肉眼验证字号效果（框标签32/面板42/计数线1.2）
- 抽查车牌识别准确率

### 3. 撰写实验报告 🔜 进行中
- 方案设计、数据处理、训练过程、mAP 评估
- v2.x vs v3.0 对比、消融分析
- Claude Code 正在撰写

### 4. 制作答辩 PPT ⬜
- 系统架构图、算法流程图、训练结果截图
- 推理效果演示（视频片段/关键帧）

---

## P1 — 建议完成

### 5. 抽查准确率
- 车流量统计误差验证（目标 ≤5%）
- 车牌号抽样对比
- 需用户肉眼确认

---

## P2 — 可选增强

### 6. OCR 微调
- 如果省份汉字漏识别 >20%
- 用 ccpd_base_plate 子集 (78,896张)
- 云端已有 ccpd.zip (1.3GB)

---

## 命令模板

### 云端推理
```bash
ssh -p 26595 root@connect.nmb2.seetacloud.com
source /root/miniconda3/etc/profile.d/conda.sh
conda activate traffic
cd /root/autodl-tmp/traffic_project
unset OMP_NUM_THREADS
screen -S infer_v5
python src/infer.py --video traffic.mp4 --vehicle-model yolov8m.pt --plate-model runs/detect/train-9/weights/best.pt --device cuda --no-gpu-ocr --half --output results/output_v5.mp4
```

### 下载结果
```bash
scp -P 26595 root@connect.nmb2.seetacloud.com:/root/autodl-tmp/traffic_project/results/output_v5.mp4 results/
```

---

## 相关文档
- [current_state.md](current_state.md) — 项目大脑
- [handoff.md](handoff.md) — 完整交接文档
