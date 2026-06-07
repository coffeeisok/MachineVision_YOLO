# session_log.md — 会话与实验记录

> 所有会话的完整复盘、踩坑记录、实验过程

---

## 会话：计算机视觉6_06_V3_车牌识别模型重训练

> 日期：2026-06-06 ~ 2026-06-07
> 起点：v2.x 烂泥状态 | 终点：v3.0 训练完成 + 推理跑通 + 文档齐全

---

### 本次会话所有重要决策

#### 决策 A：推倒 v2.x，从零重建

**问题**：v2.x 代码 9 模块 ~1500 行，YOLOv11 nano 训练 6 次全部废（mAP50-95 最高 0.28），依赖版本混乱。

**决定**：全部推倒。基于参考项目 `2/` 的成功模式重建。

**新架构**：3 个文件（`infer.py` / `plate_ocr.py` / `plate_color.py`），~350 行。

#### 决策 B：YOLOv8m 替代 YOLOv11

**为什么**：
- 参考项目 `2/` 用 YOLOv8m 成功跑通
- v2.x 用 YOLOv11 nano（2.6M 参数）训练 6 次全部 mAP<0.3
- YOLOv8m 25.9M 参数，10x 于 nano

**结果**：50 epoch → mAP50-95=0.981，比旧版提升 10 倍。

#### 决策 C：架构极简化

砍掉的模块和替代方案：

| 砍掉 | 替代 |
|------|------|
| 手动 ByteTrack 封装 (`tracking/tracker.py`) | YOLO 内置 `.track(persist=True)` |
| 手动越线计数 (`tracking/counter.py`) | supervision `LineZone` |
| 全帧双检测 + IOU 匹配 | 车辆 crop 内检测车牌 |
| `warpPerspective` 透视矫正 | 简单 `enhance()`（灰度+2x 超分+对比度） |
| 复杂格式校验正则 | `clean_plate()` 简单过滤 |

#### 决策 D：依赖全锁定

- `numpy==1.26.4` 死锁，禁止升级到 2.x
- 所有包 pin 死版本
- 后续 pip install 永远加 `--no-deps`

#### 决策 E：PaddleOCR 永远 CPU

- CUDA 12.8 与 PaddlePaddle GPU 模式不兼容 → segfault
- OCR 只处理几张车牌小图，CPU 足够快
- 不影响总速度（瓶颈在 YOLO GPU）

#### 决策 F：训练超参数固定

| 参数 | 值 | 原因 |
|------|-----|------|
| batch | 64 | 128 OOM, 64 稳 |
| workers | 4 | >4 触发 DataLoader 崩溃 |
| cache | ram | 比 disk 快 3 倍, 90GB 内存够 |
| amp | True | 省显存，精度无损 |
| epochs | 50 | 50 轮已收敛到 0.981 |

#### 决策 G：IN/OUT 方向约定

- IN = 驶近（车头面向摄像机，画面中向下运动）
- OUT = 驶离（车尾面向摄像机，画面中向上运动）
- 通过反转 LineZone 方向实现：`LINE_START=(width, line_y), LINE_END=(0, line_y)` → 向下运动=IN

#### 决策 H：推理优化

- FP16 半精度 (`--half`)：速度翻倍
- 车牌模型 imgsz 降到 480：快 1.8x
- 跳过画面顶部 30% 远处车：减少无效 OCR

---

### 为什么这么做

#### 为什么推倒而不是修补？

v2.x 的根本问题不是 bug，是**架构错了**：
- 全帧双检测 + IOU 匹配是过度设计
- YOLOv11 nano 对车牌检测来说太小
- 依赖没锁定，环境随时崩溃

继续修补 = 在错误的地基上盖楼。重来一次只用了一下午，6 次失败训练加起来浪费的时间更多。

#### 为什么选 YOLOv8m 而不是 YOLOv11？

因为**参考项目验证过**。YOLOv8m + CCPD2019 在参考项目 `2/` 里成功跑通了。YOLOv11 没有任何证据表明比 YOLOv8 好，v2.x 的 6 次失败恰恰证明选它是个错误。

#### 为什么架构这么简单？

因为**简单就够用了**。参考项目 `2/traffic_analysis_complete.py` 用一个文件跑通了所有功能。v2.x 的复杂架构（IOU 匹配、warpPerspective、手动 ByteTrack）没有带来任何效果提升，只带来了更多 bug。

#### 为什么 cache=ram 而不是 disk？

disk 模式训练太慢（磁盘 I/O 瓶颈）。90GB 物理内存足够装下 12GB 训练集 + 2GB 验证集，ram 模式快 3 倍。唯一的代价是 workers 不能太多（≤4），但这个限制不影响训练速度。

---

### 试过哪些方案

#### 训练相关

| # | 尝试 | 结果 |
|---|------|------|
| 1 | yolo11n + 100 epoch (旧 train-1~3) | 空权重，一次没跑完 |
| 2 | yolo11n + batch=32 (旧 train-4) | 22 epoch, mAP=0.14 |
| 3 | yolo11n + batch=64 (旧 train-5) | 5 epoch, mAP=0.28 |
| 4 | yolo11n + batch=64, 100 epoch (旧 train-6) | 100 epoch, mAP=0.10 |
| 5 | **yolov8m + batch=128** (train-7) | OOM，自动降到 64，但 DataLoader 崩溃 |
| 6 | **yolov8m + batch=64 + cache=disk + workers=8** (train-8) | 太慢，磁盘 I/O 瓶颈 |
| 7 | **yolov8m + batch=64 + cache=ram + workers=4** (train-9) | ✅ 成功，mAP50-95=0.981 |

#### 推理相关

| # | 尝试 | 结果 |
|---|------|------|
| 1 | PaddleOCR GPU 模式 | ❌ segfault |
| 2 | PaddleOCR CPU 模式 | ✅ 正常，速度够快 |
| 3 | 无 FP16 | 正常但慢 |
| 4 | FP16 (`--half`) | ✅ 速度翻倍，精度无损 |
| 5 | 车牌 imgsz=640 | 正常 |
| 6 | 车牌 imgsz=480 | ✅ 更快，检测效果够用 |
| 7 | 所有车都做 OCR | 远处小车牌浪费时间 |
| 8 | 跳过画面顶部 30% | ✅ 减少无效 OCR |

---

### 哪些方案失败了（不要重试）

> 这些失败方案的速查版本见 [known_issues.md](known_issues.md)，训练记录见 [training_log.md](training_log.md)

#### ❌ YOLOv11 Nano 训练车牌检测
**失败表现**：6 次训练，mAP50-95 最高 0.28，最低 0.10（随机水平）。
**根因**：yolo11n 只有 2.6M 参数，对车牌这种小目标检测来说太小。
**结论**：**永远不要用 nano 模型训练车牌检测。**

#### ❌ PaddleOCR GPU 模式
**失败表现**：`Segmentation fault` at `FusedConv2dAddActKernel`。
**根因**：CUDA 12.8 与 PaddlePaddle 2.6.2 不兼容（GPU 算子接口变更）。
**结论**：**当前环境永远用 `--no-gpu-ocr`。** 除非降 CUDA 或升级 PaddlePaddle。

#### ❌ cache=ram + workers > 4
**失败表现**：`DataLoader worker exited unexpectedly`。
**根因**：多 worker 共享内存争用 + ram 缓存占满内存。
**结论**：**cache=ram 时 workers 不要超过 4。**

#### ❌ batch=128
**失败表现**：CUDA OOM。
**根因**：RTX 3090 24GB，yolov8m + amp 跑 batch=128 刚好爆显存。
**结论**：**batch 最大 64。** 96 也许行但没试过，64 已足够。

#### ❌ cache=disk
**失败表现**：训练太慢（磁盘 I/O 瓶颈）。
**根因**：AutoDL 数据盘是 NVMe 但不是为大量随机小文件读取优化的。
**结论**：**能 ram 就 ram。** 除非内存不够（本项目 90GB 够）。

#### ❌ wget 下载 GitHub 大文件
**失败表现**：11 KB/s，50MB 文件下 1 小时还容易损坏。
**根因**：AutoDL 到 GitHub CDN 的网络很差。
**结论**：**大文件永远用 FileZilla/scp 从本地上传。**

#### ❌ v2.x 的全帧双检测 + IOU 匹配架构
**失败表现**：代码复杂，车牌识别大量错误（车身文字被当成车牌）。
**根因**：过度设计。全帧检测车牌再 IOU 匹配到车辆，比直接在车辆 crop 内检测多了一步容易出错的匹配。
**结论**：**永远在车辆 crop 内检测车牌，不要全帧检测。**

---

### 后续不要再重复尝试什么

#### 🚫 技术层面
1. **不要用 YOLOv11** — 已验证 YOLOv8m 在 CCPD 上好用，YOLOv11 训练全部失败（[decisions.md](decisions.md) §决策2）
2. **不要用 nano 模型** — 对车牌检测来说太小（[training_log.md](training_log.md) §train-1~6）
3. **不要 GPU OCR** — CUDA 12.8 不兼容（[known_issues.md](known_issues.md) §技术黑名单 #2）
4. **不要 batch > 64** — OOM（[known_issues.md](known_issues.md) §技术黑名单 #3）
5. **不要 workers > 4 (cache=ram)** — DataLoader 崩溃（[known_issues.md](known_issues.md) §技术黑名单 #4）
6. **不要从 GitHub 下载大文件到 AutoDL** — 网速太慢
7. **不要在 /tmp 放工程文件** — AutoDL 重启丢失（[known_issues.md](known_issues.md) §流程黑名单 #10）
8. **不要用 warpPerspective / IOU 匹配** — 过度设计，简单方案够用（[decisions.md](decisions.md) §决策3）

#### 🚫 流程层面
9. **不要在 v2.x 基础上修补** — 架构就是错的
10. **不要 pip install 不加 `--no-deps`** — numpy 会被升级
11. **不要不用 screen 跑长任务** — SSH 随时断
12. **不要 push 代码前不问用户** — [CLAUDE.md](../CLAUDE.md) 明确规定
13. **不要擅自删除 `dataset/`、`2/`** — 用户明确保留

---

### 当前稳定状态快照

```
训练模型: runs/detect/train-9/weights/best.pt
mAP50:    0.995
mAP50-95: 0.981
推理命令:
  python src/infer.py --video traffic.mp4 \
    --vehicle-model yolov8m.pt \
    --plate-model runs/detect/train-9/weights/best.pt \
    --device cuda --no-gpu-ocr --half \
    --output results/output_v3.mp4
稳定参数:
  batch=64, workers=4, cache=ram, amp=True, imgsz=640
```

---

---

## 实验记录：PaddleOCR 车牌微调全过程

> 日期：2026-06-06 | 状态：训练未跑完，暂停

### 一、项目目标

解决原有 PP-OCRv4 通用模型**车牌识别全部????、汉字识别失效**问题，基于 CCPD 车牌数据集微调专属车牌识别模型。

### 二、完整执行时间线

#### 阶段 1：数据集准备（无坑）
1. 本地通过 FileZilla/scp 上传 CCPD 车牌数据集（1.4G）到云端
2. 云端执行数据预处理脚本：划分训练集/验证集、生成标签文件、生成车牌字典
✅ 产出：train.txt、val.txt、plate_dict.txt

#### 阶段 2：初次搭建 PaddleOCR（埋下隐患）
1. 最初将 PaddleOCR 克隆在 **/tmp/PaddleOCR** 临时目录
2. 手动编写专属车牌训练 yml 配置文件
❌ 隐患 1：tmp 为系统临时目录，不稳定、容易冲突、文件易丢失
❌ 隐患 2：初始配置 **batch_size=128，num_workers=8**（显存/数据加载必崩）

#### 阶段 3：安装依赖引发【环境大崩溃】（最大核心坑）
执行：`pip install albumentations lmdb tqdm`
❌ 自动升级 numpy `1.26.4 → 2.2.6`
引发连环报错：
- numpy ABI 版本不匹配
- cv2 导入失败
- albumentations 库直接失效
- Paddle/GPU 无法初始化
✅ 修复：强制降级 numpy + **永久锁定 numpy 版本**，禁止自动升级
✅ 习得规则：后续所有 pip 安装必须加 `--no-deps`

#### 阶段 4：磁盘爆满问题
❌ 问题：tmp 缓存、旧代码、pip 缓存、重复 screen 会话导致系统盘占用 78%
✅ 解决方案：
- 删除 /tmp/PaddleOCR 旧工程
- 清理 pip 缓存 `pip cache purge`
- 清理无效 screen 会话 `screen -wipe`
- 将 PaddleOCR 迁移到项目目录：**/root/autodl-tmp/traffic_project/PaddleOCR**
✅ 磁盘占用从 78% → 51%

#### 阶段 5：Screen 后台会话混乱
❌ 问题：多次新建训练窗口，出现重复 `train_ocr` 会话，无法进入、冲突报错
✅ 习得操作：
- `screen -ls` 查看所有会话
- `screen -D -r 会话ID` 强制接管冲突会话
- `Ctrl+A+D` 后台挂起（不终止训练）

#### 阶段 6：模型导出报错
报错：`best_accuracy.pdparams 不存在`
❌ 原因：**训练未跑完，最优模型权重未生成**（不是命令错误）
✅ 规则：必须完整跑完 epoch，才能执行 export_model 导出推理模型

#### 阶段 7：最终训练崩溃（数据维度错误）
终极报错：`ValueError: all input arrays must have the same shape`
❌ 根源（100% 定位）：
- 配置文件未生效，依然是 **batch_size=128**
- num_workers=8 线程过多
- 车牌图片尺寸不统一，大批次无法堆叠
✅ 最终修复：批量修改为 **batch=32，workers=2**

### 三、所有报错汇总 + 根本原因 + 解决方案

| 报错现象 | 根本原因 | 解决方案 |
|---------|---------|---------|
| numpy ABI 不匹配、cv2 导入失败 | pip 自动升级 numpy 到 2.x，Paddle 只支持 1.26.4 | 强制降级 + conda 锁定 numpy 版本 |
| 系统磁盘占用过高 | tmp 临时文件、缓存、冗余代码过多 | 迁移工程、清理缓存、删除旧文件 |
| screen 会话冲突、无法进入 | 重复创建训练窗口导致 Attached 占用 | 强制接管、清理无效会话 |
| best_accuracy.pdparams 不存在 | 训练未完成，最优权重未保存 | 等待训练跑完再导出模型 |
| all input arrays must have the same shape | batch 超大、线程过多、图片尺寸不统一 | batch=32、workers=2 |
| OMP_NUM_THREADS 环境变量报错 | 线程变量非法 | export OMP_NUM_THREADS=1 |
| 模型参数 shape 不匹配警告 | 通用 OCR 字典 6625 类 → 车牌 66 类 | 正常现象，无需处理（迁移预训练权重） |

### 四、核心经验

1. **绝对不要裸装 pip 包** — 任何安装必须 `pip install xxx --no-deps`
2. **训练 batch 绝对不能乱设 128** — 真实场景图片尺寸不统一，车牌训练固定 batch=32
3. **工程绝对不能放 /tmp** — 临时目录不稳定，所有项目固定放 autodl-tmp 项目目录

### 五、最终稳定训练流程（定稿）

#### 1. 环境初始化（每次训练前）
```bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate traffic
pip install "numpy==1.26.4" --force-reinstall --no-deps 2>/dev/null
export OMP_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=0
```

#### 2. 固定正确配置
- batch_size_per_card: 32
- num_workers: 2

#### 3. 后台启动训练
```bash
cd /root/autodl-tmp/traffic_project/PaddleOCR
screen -S train_ocr
python tools/train.py -c configs/rec/plate_rec.yml
```

#### 4. 后台管理
- 退出不终止：`Ctrl+A+D`
- 恢复查看：`screen -r train_ocr`

#### 5. 训练结束后导出模型
```bash
python tools/export_model.py -c configs/rec/plate_rec.yml \
  -o Global.pretrained_model=/root/autodl-tmp/traffic_project/output/plate_rec/best_accuracy \
  Global.save_inference_dir=/root/autodl-tmp/traffic_project/output/plate_rec_infer
```

### 六、当前阶段状态

✅ 数据集完整就绪
✅ 环境彻底修复、numpy 锁定、无版本冲突
✅ 磁盘空间充足、工程目录规范
✅ 训练配置参数适配车牌场景、不会再维度报错
✅ GPU 正常启用
🟡 正在进行：60 epoch 车牌专属模型微调训练
🔜 下一步：导出推理模型 → 替换项目旧 OCR 权重 → 复测视频车牌识别效果

---

## 相关文档

- [decisions.md](decisions.md) — 本会话所有关键决策及原因
- [training_log.md](training_log.md) — 训练尝试汇总
- [known_issues.md](known_issues.md) — 失败方案黑名单
- [handoff.md](handoff.md) — 完整项目交接

---

# 会话 C：v3.1 字体修复 + 推理重跑

> 日期：2026-06-07 01:48 ~ 进行中

## 关键事件

| 时间 | 事件 |
|------|------|
| 01:48 | 推理 v3 完成（--half, output_v3.mp4 2.6GB, 486+ 车牌, IN:0 OUT:269+） |
| 01:48 | 下载 output_v3.mp4 到本地，提取 frame_early/mid/late.jpg |
| 01:50+ | 用户反馈：方框标签字太小，面板字太小，计数线字太大 |
| 01:50-02:00 | 多轮字号调整：36→48/44→28（一致化计数线）→180（5x，因字体Bug无效） |
| 02:00 | 发现根因：Pillow load_default() 回退到不可缩放 10px 位图字体 |
| 02:00-02:15 | 应用修复：FONT_PATHS 加入 wqy-zenhei.ttc, draw_labels_pil 支持 bg_color |
| 02:15 | 启动推理 v5（字体修复版），screen infer_v5 |

## 核心发现：Pillow 字体回退 Bug

**现象**：无论 font_size=36/48/180，4K 视频中文字都极小如像素点

**根因**：
1. AutoDL 镜像的 `/usr/share/fonts/` 下没有 NotoSansCJK 字体
2. `ImageFont.load_default()` 返回固定 ~10px 位图字体
3. 该字体不支持缩放，任何 font_size 都返回同大小文字

**修复**：
1. FONT_PATHS 加入 `wqy-zenhei.ttc`（Ubuntu/AutoDL 预装）
2. `load_font()` 兼容 `load_default(size=size)`（Pillow ≥10.1）
3. `draw_labels_pil()` 新增 bg_color 参数，画不透明背景矩形

## 最终渲染参数

| 元素 | 字号 | 配色 |
|------|------|------|
| 方框标签 | PIL 32 | 白字 + 深绿背景 (0,140,0) |
| 统计面板 | PIL 42 | 白字 + 深灰面板，标题红色 |
| 计数线 | text_scale=1.2 | 红色 |

## 推理记录

| # | 输出 | 字体 | 结果 |
|---|------|------|------|
| v1 | output.mp4 | 硬编码 36 | 2.6GB，未优化，字体小 |
| v3 | output_v3.mp4 | font_size=48/44 | 2.6GB，字体过小，识别486+车牌 |
| v5 | output_v5.mp4 | font_size=32/42 + bg | 🔄 运行中 |

