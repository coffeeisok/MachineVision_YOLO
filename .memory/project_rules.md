# project_rules.md — 项目规则与 AI 协作规范

> 最后更新：2026-06-07 | 适用于本项目的所有 Claude Code 会话

---

## 0. 元规则 — 项目文档组织法则

> 本段来自用户 2026-06-07 的明确指示。

1. **长期记忆统一存放**：所有长期记忆类型的内容（规则、状态、决策、日志、架构、交接）均放在 `.memory/` 目录中，根目录只保留 [CLAUDE.md](../CLAUDE.md) 和 [README.md](../README.md)
2. **分类整理**：不按日期堆砌，按类型归类——规则/状态/决策/日志/架构/交接各归各文件
3. **不省略细节**：Memory 文件承载完整信息，不允许只写指针不写内容
4. **修改前需说服**：涉及 .memory 文件的删改操作，需先向用户说明理由，获得手动授权执行
5. **Context 管理纪律**：每次准备关闭 Claude Code 或 Context 超过 70% 时，必须执行：
   - 更新所有 .memory 文件
   - 生成/更新 [handoff.md](handoff.md)（交接快照）
6. **Memory 文件与项目文档的分工**：
   - `.memory/` = AI 长期记忆（每次会话快速上手）
   - [CLAUDE.md](../CLAUDE.md) = 每次会话自动加载的全局约束
   - `README.md` = 人类阅读的完整项目说明
   - 项目根目录除上述两者外，其他 .md 均归入 `.memory/`

---

## 1. 我的偏好

### 技术选型

- **能用简单方案就不用复杂方案**。v2.x 的 IOU 匹配 + warpPerspective 被证明过度设计，v3.1 回归车辆 crop 内检测车牌
- **模型选小不选大，但别太小**。yolo11n (2.6M) 太弱 → mAP 0.10。yolov8m (25.9M) 正好 → 0.981
- **版本全锁定**。所有依赖 pin 死版本号，不让 pip 自由发挥
- **YOLOv8 优先于 YOLOv11**。参考项目验证过 YOLOv8 在车牌检测上好用，不要因为新就去试 YOLOv11
- **CPU 跑 OCR，GPU 跑检测**。PaddleOCR GPU 模式与 CUDA 12.8 不兼容 → segfault，CPU 足够快

### 操作习惯

- **训练/推理必须用 screen**。AutoDL SSH 随时可能断
- **推到 GitHub 前必须问我**。无论有没有隐含许可
- **删文件前必须问我**。数据集例外（CCPD2019.zip 等大文件确认后可删）
- **改 README 不要太频繁**，只在有实质变更时更新
- **给出命令而不是擅自执行**，云端操作经常需要用户自己跑
- **用 scp/FileZilla 传大文件**，不要指望 AutoDL 到 GitHub 的网速

### 文档规范

- README 以作者视角写，注明版本号和日期（北京时间）
- 保留历史版本信息，不要只堆叠
- 每次改动后检查 README 是否需要调整架构说明

## 2. 编码规范

### Python

- 类型标注：函数签名建议标注参数和返回类型（如 `def recognize(self, plate_img: np.ndarray) -> tuple[str, float]`）
- 注释风格：docstring 简洁，关键逻辑行内注释
- 模块上限：单个文件不超过 400 行
- 不要过度抽象：v2.x 把 tracker、counter 单独封装成模块 → v3.1 全塞进 infer.py 也很好

### 文件命名

- `src/` — 核心推理代码
- `scripts/` — 一次性数据工具
- 文件名用 snake_case
- 中文文件名尽量避免（PaddleOCR 总结那篇除外，那是历史文件）

### Git

- commit message: 版本号 + 一句话描述 + 变更清单
- 不提交大文件（.mp4/.zip/.pt/.pth）

## 3. 项目约束

### 技术约束

| 约束 | 原因 |
|------|------|
| Python 3.10 only | PaddlePaddle 不支持 3.12+ |
| numpy==1.26.4 死锁 | Paddle/PaddleOCR 不兼容 numpy 2.x |
| PaddleOCR CPU only | GPU segfault (CUDA 12.8) |
| YOLOv8 不要升级到 YOLOv11 | v2.x 已验证 YOLOv11 训练告败 |
| batch ≤ 64 | RTX 3090 24GB 上限 |
| workers ≤ 4 | cache=ram 时 DataLoader 限制 |

### 操作系统约束

- AutoDL Ubuntu 22.04
- 数据盘 `/root/autodl-tmp/` — 永久存储
- `/tmp/` — 临时目录，重启丢失，**禁止放工程文件**

### 云端禁止

- 禁止 `git push`（不与 GitHub 通信）
- 禁止安装系统级包（sudo apt 只在确需时执行）

## 4. 禁止做的事情

### 💀 绝对禁止

1. **GitHub push 之前不问用户** — [CLAUDE.md](../CLAUDE.md) 明确规定
2. **删除 `dataset/`** — 用户明确要求保留
3. **删除 `2/` 参考项目** — 调试时需要对照
4. **pip install 不加 `--no-deps`** — 会导致 numpy 被升级到 2.x
5. **训练 batch > 64** — OOM
6. **在 /tmp 下放工程文件** — AutoDL 重启丢失
7. **用 yolo11n 训练** — 已证明 mAP 极低

### ⚠️ 谨慎操作

8. **运行 PaddleOCR GPU 模式** — segfault
9. **worker > 8 + cache=ram** — DataLoader crash
10. **不经屏幕保护跑长任务** — SSH 断开丢失

## 5. 输出格式要求

### 给用户的回复

中文，清晰，带结构：

```
【任务理解】
...

【执行计划】
...

【执行步骤】
...

【结果】
...

【风险与注意事项】
...
```

### 代码修改说明

```
改动点:
- xxx.py: 做了什么，为什么

影响:
- 不影响旧功能 / 需要重新运行 XX
```

## 6. 调试流程

发现问题时：

1. **先复述问题** — 确认理解正确
2. **看日志** — 先查 `runs/detect/train-X/results.csv`、终端输出
3. **对照参考项目** — `2/` 下有过跑通的代码
4. **最小改动验证** — 改一个参数跑一次，不要一次改一堆

### 训练相关调试

- 训练崩了 → 先看是不是 OOM (batch 太大) 或 DataLoader (workers 太多)
- mAP 低 → 先检查是不是用了 nano 模型
- loss 不收敛 → 检查数据路径、标签是否正确

### 推理相关调试

- segfault → PaddleOCR GPU 模式，换 `--no-gpu-ocr`
- 车牌识别全是 Unknown → PaddleOCR 初始化失败或图片为空
- 汉字全显示 ???? → 字体文件找不到，回退默认字体

## 7. 文件组织规则

```
项目根目录/
├── src/            ← 核心推理模块（3 文件硬上限）
├── scripts/        ← 一次性数据工具脚本
├── docs/           ← 分析文档
├── dataset/        ← 训练数据（不入 git）
├── models/         ← 模型权重（不入 git）
├── results/        ← 推理输出（不入 git）
├── runs/           ← 训练记录（不入 git）
├── 2/              ← 参考项目（不动它）
├── .memory/        ← AI 长期记忆（规则/状态/决策/日志/架构）
├── CLAUDE.md       ← 唯一根目录 Agent 约束
├── README.md       ← 唯一根目录项目说明
└── data.yaml / requirements.txt / .gitignore
```

### 规则

- 新模块不超过 3 个文件。如果多了，说明过度设计
- 一次性脚本放 `scripts/`
- 配置文件放根目录（`data.yaml`, `requirements.txt`）
- 大文件全在 `.gitignore` 里

## 8. 所有长期有效的信息

- **GitHub**: `git@github.com:coffeeisok/MachineVision_YOLO.git`
- **AutoDL SSH**: `ssh -p 26595 root@connect.nmb2.seetacloud.com` (SSH key 已配置)
- **云端项目路径**: `/root/autodl-tmp/traffic_project/`
- **conda 环境**: `traffic` (Python 3.10)
- **训练产出**: `runs/detect/train-9/weights/best.pt`
- **参考视频**: `traffic.mp4` (4096×2160, 12 FPS, 452MB)
- **[CLAUDE.md](../CLAUDE.md)** — 全局 Agent 约束，每次会话必读
- **会话存档名**: `计算机视觉6_06_V3_车牌识别模型重训练`

---

## 相关文档

- [known_issues.md](known_issues.md) — §4 禁止事项的详细版
- [architecture.md](architecture.md) §五 — 目录用途速查
- [CLAUDE.md](../CLAUDE.md) §16 — 元规则（.memory 系统）
- [README.md](../README.md) — 项目说明书
