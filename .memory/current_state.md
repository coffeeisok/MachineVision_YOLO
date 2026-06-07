# current_state.md — 项目大脑

> 版本：v3.4 | 更新：2026-06-07 16:00 (北京时间) | 会话：计算机视觉6_06_V3_收尾

**快速概览**：全部完成 / GitHub 已推送(完整项目) / 本地保留提交材料 / 进度=99%

---

## 版本

**v3.4** — GitHub 完整项目推送完成。README 含图片素材，项目结构精简对外展示。

## 进度

```
█████████████████████████  99%

全部完成: 环境 ▸ 数据 ▸ 训练 ▸ 推理 ▸ 报告 ▸ PPT大纲 ▸ 素材 ▸ README ▸ GitHub
           ✅     ✅     ✅      ✅      ✅       ✅       ✅      ✅       ✅
```

| 步骤 | 状态 | 产出 |
|------|------|------|
| 全部 | ✅ | 见下方 |

## GitHub vs 本地 区别

| GitHub (完整项目源码) | 本地 only (提交材料) |
|:--|:--|
| src/ scripts/ images/ .memory/ | docs/ (报告/PPT/评分参考) |
| data.yaml requirements.txt README.md | 234081149吴博文_*.docx |
| CLAUDE.md .gitignore | CCPD2019/ dataset/ traffic.mp4 |
| | models/ runs/ results/ |

## 当前阻塞

无。

## 最近操作

- 2026-06-07 15:50：GitHub vs 本地区别确立，docs/及个人docx不上传
- 2026-06-07 15:30：README 添加 6 张图片素材 + 项目结构精简
- 2026-06-07 15:00：项目整理完成(根目录清理/requirements修正/.gitignore更新)
- 2026-06-07 14:30：.docx 报告 + PPT 大纲(v3.3) + 素材全部到位
- ⚠️ 教训：不要擅自删除本地文件，只管理 git 暂存区

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
