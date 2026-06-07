# current_state.md — 项目大脑

> 版本：v3.3 | 更新：2026-06-07 15:00 (北京时间) | 会话：计算机视觉6_06_V3_文档撰写完成

**快速概览**：全部 P0 完成 / P1=抽查验证(需用户肉眼) / P2=OCR微调(备用) / 阻塞=无 / 进度=98%

---

## 版本

**v3.3** — 实验报告(.docx)+答辩PPT大纲+12素材全部完成，进入收尾阶段。

## 进度

```
████████████████████████░  98%

环境 ▸ 数据 ▸ 训练 ▸ 推理v5/v6 ▸ .docx报告 ▸ PPT大纲 ▸ 素材 ▸ PPT制作
 ✅      ✅      ✅       ✅          ✅         ✅       ✅       🔜
```

| 步骤 | 状态 | 产出 |
|------|------|------|
| 环境搭建 | ✅ | AutoDL RTX 3090, conda traffic |
| CCPD2019 数据 | ✅ | 20k 采样 (17k train / 3k val) |
| 训练车牌检测 | ✅ | train-9 best.pt, mAP50=0.995, mAP50-95=0.981 |
| 推理 v5/v6 | ✅ | output_v5.mp4 + output_v6.mp4 (本地) |
| train-9 同步 | ✅ | runs/detect/train-9/ 已从云端同步到本地 |
| 实验报告 .docx | ✅ | 用户已完成撰写和校对 |
| 实验报告 .md | ✅ | docs/实验报告.md v3.3 (含格式规范+素材占位) |
| 答辩 PPT 大纲 | ✅ | docs/答辩PPT大纲.md v3.2 (19 Slider + Prompt + Q&A) |
| 素材采集+生成 | ✅ | images/ 目录 20 个文件，11 类素材全覆盖 |
| PPT 制作 | 🔜 | 用户进行中 |

## 当前阻塞

无。

## 最近操作

- 2026-06-07 14:55：素材全部归入 images/ 统一管理，11 类素材就绪
- 2026-06-07 14:30：生成 .docx 报告 + 优化实验报告.md 和 PPT 大纲.md
- 2026-06-07 14:19：生成素材 01/04/12（matplotlib + PIL）
- 2026-06-07 14:16：train-9 从云端同步到本地
- 2026-06-07 12:41：推理 v6 完成，output_v6.mp4 下载到本地

## 环境速查

| 项目 | 值 |
|------|-----|
| 本地 | Mac, `/Users/wucoffee/Programs/MachineVision_finalTest/` |
| 云端 | AutoDL RTX 3090, `/root/autodl-tmp/traffic_project/` |
| SSH | `ssh -p 26595 root@connect.nmb2.seetacloud.com` |
| GitHub | `git@github.com:coffeeisok/MachineVision_YOLO.git` |
| 训练产出 | `runs/detect/train-9/weights/best.pt` (mAP50-95=0.981) |
| 参考项目 | `2/` 目录（YOLOv8m + PaddleOCR + supervision LineZone，成功跑通） |
| 测试视频 | `traffic.mp4` (4096×2160, 12 FPS, 452MB, 10,813 帧) |

---

## 相关文档

- [next_tasks.md](next_tasks.md) — P0/P1/P2 待办清单
- [known_issues.md](known_issues.md) — 技术黑名单 + 已知 Bug
- [model_status.md](model_status.md) — 模型清单 + 参数
- [handoff.md](handoff.md) — 完整项目交接文档
- [architecture.md](architecture.md) — 系统架构 + 目录树
