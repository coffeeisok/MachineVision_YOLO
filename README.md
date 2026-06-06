# 计算机视觉期末项目 — 交通监控智能分析系统

> 最后更新：2026-06-06 00:30（北京时间）

## 版本历史

### v2.9 (2026-06-06 01:00) — OCR 识别模型微调

**目标**：解决 PP-OCRv4 通用模型车牌汉字识别全部 `????` 失效问题，用 CCPD 车牌数据集微调专属识别模型。

**数据集与架构：**
- CCPD `ccpd_base_plate`：78,896 张纯车牌裁剪图（1.4GB），文件名=标签
- 架构：SVTR_LCNet (PP-OCRv4)，MultiHead（CTCHead + SARHead）
- 字典切换：通用中文 6625 类 → 车牌专用 **65 类**（31 省份 + 24 字母 + 10 数字）
- 预训练权重：`ch_PP-OCRv4_rec_train`（新架构参数自动跳过不匹配层，正常现象）

**踩坑全记录（6 大坑）：**

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | numpy ABI 不匹配、cv2 崩溃 | pip 安装依赖时自动升级 numpy 1.x→2.x | 强制 `numpy==1.26.4`，所有 pip 加 `--no-deps` |
| 2 | 系统盘 78% 爆满 | /tmp 临时文件 + pip 缓存 + 旧 screen 会话 | 迁移到项目目录 + `pip cache purge` + `screen -wipe` |
| 3 | /tmp/PaddleOCR 不稳定 | 临时目录，重启丢失、权限冲突 | 克隆到 `traffic_project/PaddleOCR` |
| 4 | 训练启动时 segfault | batch=128 + num_workers=8 → 共享内存爆仓 + 坏图 | batch=32, num_workers=2 |
| 5 | "all input arrays must have the same shape" | 车牌尺寸不统一，大批次张量堆叠失败 | batch=32 确保维度对齐 |
| 6 | best_accuracy.pdparams 不存在 | 训练未跑完即尝试导出 | 等完整 epoch 跑完再 export |

**最终稳定配置：**

| 参数 | 初始值（翻车） | 最终值（稳定） |
|------|:---:|:---:|
| batch_size_per_card | 128 | **32** |
| num_workers | 8 | **2** |
| learning_rate | 0.0005 | 0.0005 (Cosine+warmup) |
| epoch | 60 | 60 |
| numpy | 自动升级 | **锁定 1.26.4** |

**训练命令：**
```bash
cd /root/autodl-tmp/traffic_project/PaddleOCR
source /root/miniconda3/etc/profile.d/conda.sh && conda activate traffic
pip install "numpy==1.26.4" --force-reinstall --no-deps -q
export OMP_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=0
screen -S train_ocr
python tools/train.py -c configs/rec/plate_rec.yml
# Ctrl+A+D 挂起，screen -r train_ocr 恢复
```

**状态**：🟡 训练中（60 epoch），后续：导出模型 → 替换项目 OCR 权重 → 复测验证

Claude code存档name：“ 计算机视觉期末_6_05_车流yes，车牌汉字no ”

### v2.8 (2026-06-05 23:00)

**融合参考项目 + 自研策略：**

- **车牌模型升级**：`plate_best.pt` 从 yolo11n (5.2MB) 替换为参考项目 yolo8m (198MB)，模型容量 10 倍提升
- **OCR 策略融合**：参考项目 `clean_plate()` 过滤非法字符 + `enhance()` 灰度→2x上采样→对比度→模糊，替代复杂格式校验 + CLAHE
- **颜色识别融合**：参考项目 HSV 范围 + 8% 最低阈值 + 最佳匹配方式
- **缓存重试机制**：已识别车牌缓存复用，未识别 track 每 10 帧重试
- **PaddleOCR 改用 CPU**：规避 CUDA 12.8 兼容性 segfault

### v2.7 (2026-06-05 16:30)

**架构重构 — 全帧双检测 + 透视矫正：**

- **删除「下 1/3 裁剪 OCR」兜底方案**：该方案是假车牌输出的根源（车身文字被当成车牌），改为全帧车牌检测 + IOU 匹配
- **全帧车牌检测**：`plate_model` 改为对整帧推理（原为对整车 crop 推理），`--plate_imgsz` 默认 1920（4K 视频下车牌不再被压缩消失）
- **IOU 匹配**：车牌 bbox → 判断车牌中心落在哪个车辆 bbox 内 → 关联 track_id，每 track 保留面积最大的车牌帧
- **透视矫正**：新增 `PlateRecognizer.perspective_correct()`，Canny 找四边形 → `warpPerspective` 拉正梯形车牌 → OCR
- **格式校验收紧**：`_is_plate_format()` 强制省份简称前缀，删除 `alpha_count >= 4` 宽松兜底，杜绝 `你pick谁` 类假输出

**新增参数：**
- `--plate_imgsz 1920`：车牌检测独立输入尺寸
- `--plate_every 1`：车牌检测帧间隔（1=逐帧）

### v2.6 (2026-06-05 10:46)

**Bug 修复（3 项）：**
- **修复车牌识别失败**：新增 `recognize_with_preprocess()` 方法（裁剪下1/3 → 2x上采样 → CLAHE增强 → OCR），解决远景小目标车牌漏检
- **修复车流数据检测不到**：`ByteTrackWrapper` 帧率不再硬编码25，改为由 `infer.py` 传入视频真实 FPS；`counter.py` 补回 `min_cross_dist=20` 位移过滤
- **修复车辆类型分类不准**：车辆模型默认从 `yolo11n.pt` 升级为 `yolo11s.pt`；新增 `--vehicle_conf` 参数（默认 0.35）过滤低置信度误分类

**新增：**
- `infer.py` 新参数：`--vehicle_conf 0.35`、`--vehicle_model` 默认 `yolo11s.pt`
- 第一步新增 2.5 节「上传本地代码到 AutoDL」（FileZilla SFTP 方法）
- 第十一步项目结构替换为云端 `tree -L 3` 实际输出

### v2.5 (2026-06-05 00:50)

- 视频替换为 4K 原视频 (4096×2160, 451MB)，车牌清晰度大幅提升
- `infer.py` 横截线自动按画面 53% 计算 (`--line_y 0`)，适配任意分辨率
- `infer.py` 双模型架构：vehicle (COCO) + plate (CCPD2019 训练)
- `counter.py` 最小位移 20px 过滤静止车抖动，消除假 forward
- OCR 双层兜底：plate_best.pt → PaddleOCR 自带检测 + 格式正则过滤
- 颜色 HSV 阈值放宽 (蓝 95-135, 绿 35-85, 黄 15-40), 最低占比降至 15%
- OCR 置信度阈值降至 0.3，格式检查放宽（4+ ASCII 即接受）

### v2.3 (2026-06-04 16:20)

- PaddleOCR 降级至 2.7.3 + opencv-python 4.8.1.78 + numpy<2（3.x 与当前环境不兼容）
- OCR 测试通过：PaddleOCR 2.7 返回格式 `[[bbox, (text, conf)]]`，识别准确率 0.996
- `requirements.txt` 锁定兼容版本号，防止依赖链冲突
- tracker 适配 supervision >= 0.23 API（`sv.ByteTrack`）
- 推理管线首次跑通：253 辆车跟踪计数，output.mp4 生成
- 视频实际参数：1280×674, 12 FPS（非假设的 1920×1080, 25FPS）

### v2.2 (2026-06-04 15:20)

- API 适配：`supervision` ByteTrack 改为 `sv.ByteTrack`（v0.28+ 兼容）
- API 适配：`PaddleOCR` 3.x 精简参数，首次运行自动下载模型
- `train.py`：batch 32→64, workers 8→12, 新增 cache=True
- 训练产出确认：100 epoch, mAP50-95 0.98

### v2.1 (2026-06-04)

- 合并原第三/四步（抽帧+标注）为「数据集准备」，适配 CCPD2019 已标注数据
- 新增 `scripts/convert_ccpd.py`：CCPD2019 文件名标注 → YOLO .txt 格式转换
- 重写 `scripts/split_dataset.py`：支持 `--max_samples` 限制采样量，默认 20000 张
- 所有脚本改为基于 `__file__` 定位项目根目录，任意目录执行均可
- 步骤重新编号为 1~11，删除冗余的标注/LabelImg 内容
- 数据说明：标注工作量已移除，流程简化为 CCPD2019 直转直训

### v2.0 (2026-06-03 23:50)

- 统一技术栈为 **YOLOv11**（与方案选型一致，替换原 YOLOv8）
- 补全**视频数据集**章节（来源/格式要求/上传方法/预处理脚本）
- 细**车牌颜色识别**：新增 HSV 阈值表、`plate_color.py` 完整代码、5 种容错策略
- 补全全部代码模块：`tracker.py`、`counter.py`、`plate_ocr.py`、`plate_color.py`、`infer.py`
- 步骤重组：去掉"第X天"，改为按逻辑顺序的"第X步"
- 删除建议时间安排表，替换为提交清单
- 新增自训练路线确认 + 标注建议
- 项目结构加入完整子目录和文件注释

### v1.0 (原始版本)

- 基于参考文档「在实战中学AI-车流量统计项目」整理
- 包含 12 阶段操作步骤（AutoDL 环境搭建 → 答辩准备）
- 技术栈：YOLOv8 + ByteTrack + PaddleOCR

---

## 项目进度

```
████████████████████░░  ~90%

环境 ▸ 数据 ▸ 训练(车牌检测) ▸ 推理管线(v2.8) ▸ OCR微调(v2.9) ▸ 验证 ▸ 报告 ▸ PPT
```

| # | 步骤 | 状态 | 说明 |
|---|------|------|------|
| 1 | 准备环境 | ✅ | AutoDL + RTX 5090 + traffic 环境 |
| 2 | 获取数据 | ✅ | CCPD2019 12万张 + traffic.mp4 |
| 3 | 数据集准备 | ✅ | 转换+采样2万张，85/15 划分 |
| 4 | 训练车牌检测 | ✅ | 100轮(train-6)，mAP50-95 0.98 |
| 5 | 推理管线 | ✅ | 车牌 OCR 输出正常，显示到视频画面 |
| 6 | 横截线调优 | ✅ | 自动按画面 53% 计算，4K 视频 line_y=1144 |
| 7 | Bug修复(v2.6) | ✅ | 车牌识别/车流计数/车型分类 三项修复 |
| 8 | 架构重构(v2.7) | ✅ | 全帧双检测+IOU匹配+透视矫正 |
| 9 | 融合参考项目(v2.8) | ✅ | 198MB车牌模型+OCR融合+缓存重试 |
| 10 | OCR模型微调(v2.9) | 🔄 | CCPD 7.8万张，PP-OCRv4 SVTR_LCNet，60 epoch |
| - | 实验报告 | ⬜ | 未写 |
| - | 答辩PPT | ⬜ | 未做 |

---

## 项目要求

设计并实现一个系统，对某段交通监控摄像头的视频进行智能分析，完成以下任务：

1. 统计出该段视频内的车流量；
2. 提取出所通过的车辆的车牌号码及该车牌底色（蓝色、绿色、黄色、其他）信息。

完成项目，包括数据的收集整理、模型的训练、系统的部署集成等。所需提交的材料包括：实验报告、项目完整代码（含训练、部署说明）和项目汇报PPT，详细要求请参阅附件[综合项目考核评分参考.pdf](综合项目考核评分参考.pdf)

## 参考文档内容

### 在实战中学AI-车流量统计项目-开篇

在日常工作以及互联网上，经常有人问，该如何做好一个AI项目？为啥我的模型效果一直不行？AI看似那么牛，为啥时常犯傻？我该在项目上怎么用好AI这个工具？工作这么多年，听到过新毕业的小白同学在问；也有资深的产品以及技术大咖在问；甚至很多不了解AI但想引入AI到他们业务流中的“老板们”也想知道。

作为一个在这个行业里摸爬滚打了八、九年的老油条，有一些自己的看法，想分享给大家，也想从大家那里获取到一些不一样的理解。以前零零碎碎写过一些文章，也获得过一些同学的认可，回过头来看，却是有些太琐碎，也不系统，不太利于自己的沉淀，也不利于别人系统的了解AI的落地过程。大家工作过的都知道，在实战中学习和积累的是最快的，所以寻思着，是不是可以向大家展示一下，作为一个技术同学，实际落地一个AI项目是什么样的一个过程，这样大家了解的更系统，我自己也可以通过咀嚼下过往，理解的更深刻。

基于上面的考虑，寻思着可以出个这样的系列，作为第一个项目，希望能涵盖AI落地的基础路径，理解成本也没那么高，就选择了一个常规的安防场景-车流量统计。下面让我们以一个算法工程师的角度，看如何研发一套可用的车流量统计算法系统。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_gif/Hg8IiasWC4WobRhXaia6nazg8OIdUGhqfT5gBLFCiadF03Ej1IE6lPD4FSgA1GmsKavKpuyM9ib1A2sgIXAxCTyuFg/640?wx_fmt=gif&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=0)

### 需求分析

车流量即单位时间内通过某路段或交通点的车辆数目。在交通规划中，车流量的统计数据是设计道路、制定交通政策和评估交通项目效果的重要依据。通过对车流量的监测和分析，有关部门可以了解道路的拥堵状况，从而采取相应的措施。本项目的输入为道路上监控摄像头的视频流数据，输出为统计时间段内的车流量均值。

### 车流量的定义

任何一个算法项目，需求定义清楚是可以进行后面研发的基础，所以，首先要确认什么叫“车流量”，这部分的定义不是上面的那种名词解释，而是面向计算机可以理解的了的定义。定义好问题，也是算法工程师非常重要的技能。

这个项目关注场景为安放在道路中间的摄像头，视野可涵盖正向（即迎着摄像头方向）和反向（即顺着摄像头方向）行驶的车辆，需分别统计客户指定时间段内，正向和反向主路上车流量均值。在关注行驶方向上定义与道路垂直的横截线，越过该线的车辆即计数，并用于统计车流量。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_jpg/Hg8IiasWC4WobRhXaia6nazg8OIdUGhqfTPf2wfk60P7ZJVbLG4JkEHAzEpN5dY78RYr8pZ0ia6HIlme8bGkOU2PA/640?wx_fmt=jpeg&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=1)



#### 性能指标要求

车流量统计值与真实偏差5%以内；处理效率为单服务器同时处理10路数据。

#### 数据输入输出

系统对接前端管理平台，输入数据为前端摄像头采集的RTSP流，分辨率为1080P，帧率25FPS；统计开始信号；统计结束信号；触发车流量统计的横截线；均由管理平台下发。系统输出统计时间段内的平均车流量，反馈管理平台。

#### 系统部署平台

ubuntu20.04服务器，搭配3080显卡，16核 单核3.6G Hz CPU处理器。

### 方案选型

#### 算法方案选型

本项目适用目标跟踪后提取轨迹线，利用轨迹线与道路横截线的相对关系统计车流量。

1. 在视觉识别算法方面，该场景关注的车辆属于常规的目标，使用YOLOv11做目标检测，ByteTrack做目标跟踪，即可满足需求。
2. 在业务算法方面，车辆跟踪后以车尾边的中心点形成轨迹线，判断轨迹线是否跨越横截线，跨越哪条横截线，即对应行驶方向的车流数量加一。

进一步地，

1. 对于车辆属性信息的提取，则可对跨越横截线的每个车辆跟踪轨迹取一张包括车辆全身且未被遮挡的图像进行图像分类处理。
2. 对于车牌信息的提取，可对跨越横截线的每个车辆跟踪轨迹取一张包括车辆全身且未被遮挡的图像进行车牌检测，取一张车牌区域没有被其他车辆遮挡的图像进行OCR、车牌区域颜色统计分析。



## 操作步骤

技术栈（统一使用 YOLOv11，与方案选型一致）：

```text
AutoDL（RTX5090）
+
YOLOv11
+
ByteTrack
+
PaddleOCR
```

那我不给你讲一堆理论，直接按「从零开始做到答辩演示」的顺序写。

目标：

```text
输入：
交通监控视频

输出：
车流量统计
车辆ID跟踪
车牌号码
车牌颜色
结果视频
```

达到课程设计优秀标准。

------

## 第一步：准备环境

#### 1 登录AutoDL

进入控制台

打开：

```text
JupyterLab
```

不要直接用终端开发。

后面：

- 写代码
- 看图片
- 看训练结果

都方便。

------

#### 2 创建项目目录

打开Terminal

```bash
cd /root/autodl-tmp

mkdir traffic_project

cd traffic_project
```

创建结构：

```bash
mkdir dataset
mkdir models
mkdir train
mkdir tracking
mkdir ocr
mkdir color
mkdir deploy
mkdir scripts
mkdir results
```

最终：

```text
traffic_project
│
├── dataset
├── models
├── scripts
├── train
├── tracking
├── ocr
├── color
├── deploy
└── results
```

------

### 2.5 上传本地代码到 AutoDL

本项目在**本地编写代码**，通过 **FileZilla** 上传到 AutoDL 云端执行训练和推理。

**FileZilla 连接 AutoDL：**

1. 打开 FileZilla，点击「文件 → 站点管理器 → 新站点」
2. 填写连接信息：

| 字段 | 值 |
|------|-----|
| 协议 | SFTP - SSH File Transfer Protocol |
| 主机 | AutoDL 实例的 SSH 地址（控制台可复制） |
| 端口 | AutoDL 实例的 SSH 端口 |
| 用户名 | `root` |
| 密码 | AutoDL 实例的 SSH 密码 |

3. 点击「连接」

**首次部署（新主机）——上传全部文件：**

左侧（本地）导航到项目目录，右侧（远程）导航到 `/root/autodl-tmp/traffic_project/`，将以下文件/文件夹拖拽上传：

```text
deploy/        → /root/autodl-tmp/traffic_project/deploy/
ocr/           → /root/autodl-tmp/traffic_project/ocr/
color/         → /root/autodl-tmp/traffic_project/color/
tracking/      → /root/autodl-tmp/traffic_project/tracking/
scripts/       → /root/autodl-tmp/traffic_project/scripts/
train/         → /root/autodl-tmp/traffic_project/train/
models/        → /root/autodl-tmp/traffic_project/models/
data.yaml      → /root/autodl-tmp/traffic_project/data.yaml
requirements.txt → /root/autodl-tmp/traffic_project/requirements.txt
check_dependencies.py → /root/autodl-tmp/traffic_project/check_dependencies.py
yolo11s.pt     → /root/autodl-tmp/traffic_project/yolo11s.pt
traffic.mp4    → /root/autodl-tmp/traffic_project/traffic.mp4
```

> `traffic.mp4` (451MB) 和 `yolo11s.pt` (18MB) 较大，建议用 scp 传：
> ```bash
> # 本地执行
> scp -P <端口> traffic.mp4 root@<IP>:/root/autodl-tmp/traffic_project/
> scp -P <端口> yolo11s.pt root@<IP>:/root/autodl-tmp/traffic_project/
> ```

**增量更新——仅上传变更文件：**

```text
deploy/infer.py   → /root/autodl-tmp/traffic_project/deploy/infer.py
ocr/plate_ocr.py  → /root/autodl-tmp/traffic_project/ocr/plate_ocr.py
```

> **注意**：`dataset/`、`results/` 是云端产物或大数据文件，不要上传（已在云端生成或单独上传）。

------

#### 3 创建虚拟环境

不要直接污染系统环境。

```bash
conda create -n traffic python=3.10 -y

conda activate traffic
```

检查：

```bash
python -V
```

应显示：

```text
Python 3.10.x
```

#### 4. 激活traffic环境

执行：

```bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate traffic

cd ~/autodl-tmp/traffic_project
```

再检查：

```bash
python -V
```

应该变成：

```bash
Python 3.10.x
```

------

#### 5. 安装依赖

一次装齐。

```bash
pip install ultralytics
pip install opencv-python
pip install supervision
pip install paddleocr
pip install paddlepaddle
pip install matplotlib
pip install pandas
```

**测试依赖可用性：**

```bash
python check_dependencies.py
```



```bash
yolo checks
# output:
```

------



#### 6. 测试GPU

```bash
python
```

输入：

```python
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
```

应该输出：

```text
True
RTX 5090
```

------

## 第二步：获取数据

### 图片数据集

1. **使用 `wget`**

```bash
wget -O CCPD2019.zip "https://ai-studio-online.bj.bcebos.com/v1/c533b3a2a4cb4ff79ffecdefb678575dc75926610266424cafe3b92b087def5f?responseContentDisposition=attachment%3Bfilename%3DCCPD2019.zip&authorization=bce-auth-v1%2FALTAKzReLNvew3ySINYJ0fuAMN%2F2026-06-03T08%3A10%3A21Z%2F60%2F%2F3c595984bed5190d75afbb32659753b1df88f95cae9fdeec0833a12973d64b4e"
```

2. **安装 unzip 工具**

```bash
sudo apt install unzip -y
```

3. **解压数据集**

```bash
# 将其解压到一个名为 CCPD2019 的专属目录中，避免文件散落在当前文件夹
unzip CCPD2019.zip -d CCPD2019/
```

------

### 视频数据

路径：/Users/wucoffee/Programs/MachineVision_finalTest/traffic.mp4

#### 视频格式

```text
格式:     MP4 (H.264)
分辨率:   4096×2160 (DCI 4K)
帧率:     12 FPS
时长:     15 分钟, 10812 帧
大小:     451 MB
视角:     高位俯拍，单向车流
特点:     4K 分辨率，车牌区域像素充足，适合 OCR 识别
```

#### 上传到 AutoDL

本地准备好 `traffic.mp4` 后，在 JupyterLab 中通过文件管理器上传到 `/root/autodl-tmp/traffic_project/`。

也可以使用 scp 上传（在本地终端执行）：

```bash
scp -P <端口> traffic.mp4 root@<AutoDL_IP>:/root/autodl-tmp/traffic_project/
```



## 第三步：数据集准备

CCPD2019 已下载到 `/root/autodl-tmp/CCPD2019/`。但它的标注编码在文件名里（如 `025-95_113-154&383_386...jpg`），不是 YOLO 格式的 `.txt`。需要两步处理。

### 3.1 格式转换：CCPD2019 → YOLO

```bash
cd /root/autodl-tmp/traffic_project
python scripts/convert_ccpd.py
```

脚本会自动查找 `/root/autodl-tmp/CCPD2019`，无需手动指定路径。这一步做的事：
- 解析每个文件名中的车牌四角坐标（`x1&y1_x2&y2_x3&y3_x4&y4`）
- 转为 YOLO 格式 bbox (class_id x_center y_center width height)
- 图片 → `dataset/ccpd_yolo/images/`
- 标签 → `dataset/ccpd_yolo/labels/`

### 3.2 划分训练/验证集

```bash
python scripts/split_dataset.py
```

默认从 `dataset/ccpd_yolo` 采样 20000 张，85/15 划分为 train/val。CCPD2019 `ccpd_base` 有 ~96k 张，全量训练没必要——20k 够用且快得多。

结果：

```text
dataset/
├── ccpd_yolo/               # 转换后的全量数据（中间产物）
├── images/
│   ├── train/               # ~17000 张
│   └── val/                 # ~3000 张
└── labels/
    ├── train/               # YOLO 格式标签
    └── val/
```

### 3.3 验证

```bash
echo "训练集: $(ls dataset/images/train/*.jpg | wc -l) 张"
echo "验证集: $(ls dataset/images/val/*.jpg | wc -l) 张"
```

### 3.4 （可选）从视频抽帧

如果之后需要用其他视频做推理测试：

```bash
python scripts/extract_frames.py --video ../traffic.mp4 --interval 10
```

## 第四步：训练车牌检测模型

项目需要两个检测模型，但只需要训练一个：

| 模型 | 用途 | 数据 | 需要训练？ |
|------|------|------|-----------|
| YOLOv11（车牌检测） | 从车辆区域中找到车牌 | CCPD2019 → 刚划分的 dataset/ | ✅ 本步训练 |
| YOLOv11（车辆检测） | 从视频中找到车辆 | COCO 预训练权重 | ❌ 直接推理，car/bus/truck 原生支持 |

`data.yaml` 已就绪（`path: dataset`，单类 `0: plate`）。`train/train.py` 默认参数已针对 RTX 5090 优化：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| batch | 64 | 5090 32GB 显存轻松吃下 |
| workers | 12 | 数据加载不拖后腿 |
| cache | True | 20k 张图全载入 RAM，消除磁盘 I/O |

```bash
cd /root/autodl-tmp/traffic_project
python train/train.py
```

**暂停/恢复训练**：

```bash
# Ctrl+C 暂停（每个 epoch 结束自动保存 last.pt）
# 恢复：
python -c "
from ultralytics import YOLO
model = YOLO('runs/detect/train/weights/last.pt')
model.train(resume=True)
"
```

训练完成后，把最优权重复制到 models/：

```bash
cp runs/detect/train/weights/best.pt models/plate_best.pt
```

------

## 第五步：查看训练效果

训练完成：

```text
runs/detect/train
```

里面有：

```text
results.png

confusion_matrix.png

best.pt
```

重点保存：

```text
best.pt
```

------

这是答辩核心材料。

评分标准要求训练过程和评估结果。

------

## 第六步：车辆跟踪

原理：

```text
YOLO → 检测车辆 → ByteTrack → 分配ID
ID 1, ID 2, ID 3... 同一辆车保持同一ID
```

创建 `tracking/tracker.py`：

```python
"""
tracking/tracker.py
ByteTrack 跟踪器封装，基于 supervision >= 0.23
"""
import numpy as np
import supervision as sv


class ByteTrackWrapper:
    """ByteTrack 封装，返回带 tracker_id 的 Detections

    frame_rate 必须与视频实际 FPS 一致，否则卡尔曼滤波的
    状态预测步长错误，导致 track 提前死亡或漂移严重。
    """

    def __init__(self, frame_rate: int):
        if frame_rate <= 0:
            raise ValueError(f"frame_rate 必须 > 0，实际传入: {frame_rate}")
        self.tracker = sv.ByteTrack(frame_rate=frame_rate)

    def update(self, detections: sv.Detections) -> sv.Detections:
        if len(detections) == 0:
            detections.tracker_id = np.array([], dtype=int)
            return detections

        tracked = self.tracker.update_with_detections(detections)
        return tracked
```

------

效果：

```text
车A 一直是 ID=7
车B 一直是 ID=13
```

------

## 第七步：车流量统计

核心算法：**跨立实验**——判断车辆轨迹线段是否与横截线相交。

```text
前帧位置 (x_prev, y_prev)
        │
        │  轨迹线段
        │
当前帧位置 (x_curr, y_curr)
        │
════════╪═══════════  横截线 LINE_Y
        │
```

创建 `tracking/counter.py`：

```python
"""
tracking/counter.py
越线判断 + 双向车流量统计（带最小位移过滤）
"""
import supervision as sv


class LineCounter:
    def __init__(self, line_y: int = 360, min_cross_dist: float = 20):
        self.line_y = line_y
        self.min_cross_dist = min_cross_dist  # 过滤 bbox 抖动

        self.forward_count = 0
        self.backward_count = 0
        self.prev_positions: dict[int, float] = {}
        self.counted: dict[int, str] = {}

    def update(self, detections: sv.Detections) -> list[tuple[int, str]]:
        crossed = []
        for i, track_id in enumerate(detections.tracker_id):
            tid = int(track_id)
            y1 = detections.xyxy[i][1]
            y2 = detections.xyxy[i][3]
            center_y = (y1 + y2) / 2.0

            if tid in self.prev_positions:
                prev_y = self.prev_positions[tid]
                if abs(center_y - prev_y) < self.min_cross_dist:
                    continue

                if prev_y < self.line_y <= center_y and tid not in self.counted:
                    self.forward_count += 1
                    self.counted[tid] = "forward"
                    crossed.append((tid, "forward"))
                elif prev_y > self.line_y >= center_y and tid not in self.counted:
                    self.backward_count += 1
                    self.counted[tid] = "backward"
                    crossed.append((tid, "backward"))

            self.prev_positions[tid] = center_y
        return crossed

    def get_direction(self, track_id: int) -> str:
        return self.counted.get(track_id, "")

    @property
    def total_count(self) -> int:
        return self.forward_count + self.backward_count
```

------

## 第八步：车牌识别

创建 `ocr/plate_ocr.py`：

```python
"""
ocr/plate_ocr.py
基于 PaddleOCR 2.7 的车牌识别模块。

双路径策略：
  路径A: recognize(plate_crop)              — 已知车牌区域，直接 OCR
  路径B: recognize_with_preprocess(vehicle_crop) — 从整车图中定位+识别
          ① 裁剪下 1/3 区域（车牌通常在此）
          ② 2x 超分辨率上采样（解决小目标问题）
          ③ CLAHE 对比度增强
          ④ PaddleOCR 检测+识别
"""
import cv2
import numpy as np
from paddleocr import PaddleOCR


class PlateRecognizer:
    """车牌文字识别器"""

    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)

    def _is_plate_format(self, text: str) -> bool:
        """判断文本是否符合中国车牌格式"""
        import re
        clean = text.replace(" ", "").replace("-", "").replace("·", "")
        if len(clean) < 5 or len(clean) > 12:
            return False
        pattern = r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青藏琼宁][A-Z][A-Z0-9]{5,6}$'
        if re.match(pattern, clean):
            return True
        alpha_count = sum(1 for c in clean if c.isascii() and (c.isalpha() or c.isdigit()))
        return alpha_count >= 4 and len(clean) <= 8

    def recognize(self, vehicle_img: np.ndarray) -> str:
        """从车辆图像中识别车牌号码，优先选择符合车牌格式的结果"""
        if vehicle_img is None or vehicle_img.size == 0:
            return ""

        try:
            results = self.ocr.ocr(vehicle_img, cls=True)
            if not results or not results[0]:
                return ""

            candidates = []
            for line in results[0]:
                item = line[1]
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    text, conf = item[0], item[1]
                    clean = text.replace(" ", "").replace("-", "").replace("·", "")
                    candidates.append((clean, conf))

            if not candidates:
                return ""

            plate_like = [(t, c) for t, c in candidates if self._is_plate_format(t)]
            pick = max(plate_like, key=lambda x: x[1]) if plate_like else max(candidates, key=lambda x: x[1])
            text, conf = pick
            if conf < 0.3:
                return ""
            return text

        except Exception:
            return ""

    def recognize_with_preprocess(self, vehicle_img: np.ndarray,
                                  upscale: float = 2.0) -> str:
        """
        针对监控远景小目标车牌的识别方法。

        步骤：
          1. 裁剪车辆下 1/3 区域（车牌通常在此）
          2. 上采样放大（默认 2x），补偿小尺寸导致的 OCR 失败
          3. CLAHE 对比度增强
          4. PaddleOCR 检测 + 识别
        """
        if vehicle_img is None or vehicle_img.size == 0:
            return ""

        try:
            h, w = vehicle_img.shape[:2]
            lower_third = vehicle_img[int(h * 0.65):h, :]
            if lower_third.size == 0:
                return ""

            new_w = int(w * upscale)
            new_h = int(lower_third.shape[0] * upscale)
            if new_w < 80 or new_h < 20:
                new_w = max(new_w, 160)
                new_h = max(new_h, 40)
            upsampled = cv2.resize(lower_third, (new_w, new_h),
                                   interpolation=cv2.INTER_CUBIC)

            gray = cv2.cvtColor(upsampled, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

            return self.recognize(enhanced_bgr)
        except Exception:
            return ""

    def detect_plate_region(self, vehicle_img: np.ndarray) -> np.ndarray | None:
        """边缘检测定位车牌区域（路径B 的备选方案）"""
        if vehicle_img is None or vehicle_img.size == 0:
            return None

        h, w = vehicle_img.shape[:2]
        lower = vehicle_img[int(h * 0.6):h, :]

        gray = cv2.cvtColor(lower, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 200)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(
            closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        for cnt in sorted(contours, key=cv2.contourArea, reverse=True):
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect_ratio = bw / bh if bh > 0 else 0
            if 3.0 < aspect_ratio < 5.5 and bw > 60:
                return lower[y:y + bh, x:x + bw]

        return None
```

------

## 第九步：车牌颜色识别

不用训练，OpenCV 的 HSV 颜色空间 + 像素占比规则即可。中国车牌颜色有明确国标，不同颜色对应不同车辆类型。

### 原理

1. 将车牌区域图像从 BGR 转为 HSV
2. 对每个像素判断其 HSV 值落在哪个颜色的阈值范围内
3. 统计各颜色的像素占比
4. 占比 > 30% 的颜色即为车牌底色

### HSV 颜色阈值表

这些阈值是根据中国车牌国标颜色 + 实际光照条件调试得到的经验值：

| 颜色 | H 范围 | S 范围 | V 范围 | 对应车牌 |
|------|--------|--------|--------|---------|
| 蓝色 | 100~130 | 50~255 | 50~255 | 小型车蓝牌 |
| 绿色 | 40~80 | 50~255 | 50~255 | 新能源绿牌 |
| 黄色 | 20~35 | 50~255 | 100~255 | 大型车/教练车黄牌 |
| 其他 | - | - | - | 白色(警车)、黑色(使馆)等 |

> **注意**：OpenCV 中 H 范围是 0~180（不是 0~360），S 和 V 范围是 0~255。

### 创建 `color/plate_color.py`

```python
import cv2
import numpy as np


# HSV 颜色阈值定义（OpenCV: H∈[0,180], S∈[0,255], V∈[0,255]）
COLOR_RANGES = {
    "Blue": {
        "lower": np.array([95, 40, 40]),
        "upper": np.array([135, 255, 255]),
    },
    "Green": {
        "lower": np.array([35, 40, 40]),
        "upper": np.array([85, 255, 255]),
    },
    "Yellow": {
        "lower": np.array([15, 50, 80]),
        "upper": np.array([40, 255, 255]),
    },
}


def classify_plate_color(plate_img: np.ndarray, threshold: float = 0.30) -> str:
    """
    识别车牌底色

    Args:
        plate_img: 车牌区域BGR图像
        threshold: 判定为某颜色的最小像素占比(默认30%)

    Returns:
        "蓝色" / "绿色" / "黄色" / "其他"
    """
    if plate_img is None or plate_img.size == 0:
        return "其他"

    hsv = cv2.cvtColor(plate_img, cv2.COLOR_BGR2HSV)
    total_pixels = hsv.shape[0] * hsv.shape[1]

    if total_pixels == 0:
        return "其他"

    for color_name, ranges in COLOR_RANGES.items():
        mask = cv2.inRange(hsv, ranges["lower"], ranges["upper"])
        ratio = np.sum(mask > 0) / total_pixels
        if ratio > threshold:
            return color_name

    return "其他"


def classify_plate_color_dominant(plate_img: np.ndarray) -> str:
    """
    备选方案：按占比最大的颜色返回（带回退逻辑）
    当默认阈值方案返回"其他"时，可以用这个兜底。
    """
    if plate_img is None or plate_img.size == 0:
        return "其他"

    hsv = cv2.cvtColor(plate_img, cv2.COLOR_BGR2HSV)
    total_pixels = hsv.shape[0] * hsv.shape[1]

    if total_pixels == 0:
        return "其他"

    ratios = {}
    for color_name, ranges in COLOR_RANGES.items():
        mask = cv2.inRange(hsv, ranges["lower"], ranges["upper"])
        ratios[color_name] = np.sum(mask > 0) / total_pixels

    best_color = max(ratios, key=ratios.get)

    # 如果最好颜色占比都不到10%，说明确实不是标准蓝/绿/黄牌
    if ratios[best_color] < 0.10:
        return "其他"

    return best_color
```

### 容错与边界情况处理

| 情况 | 处理方式 |
|------|---------|
| 车牌区域为空 | 返回 "其他" |
| 光照过暗(V过低) | 黄色阈值 V≥100 可过滤暗部噪点 |
| 多个颜色均超30% | 按优先级：蓝 > 绿 > 黄 > 其他 |
| 占比均不足 | 调用 `classify_plate_color_dominant` 兜底 |
| 白牌(警车)误判 | 白色在HSV中 S<50，不在任何预定义范围内，自然归为"其他" |

------

## 第十步：结果渲染与主推理管线

`deploy/infer.py` 串联所有模块。**v2.8 全帧双检测 + 缓存重试架构**。

> v2.9 OCR 微调完成后，需在 `ocr/plate_ocr.py` 中指向微调推理模型目录。

当前状态：车辆检测+计数✅ | 车牌检测(198MB模型)✅ | OCR(通用PP-OCRv4,汉字弱🔧) | 颜色识别✅

```text
视频帧
  │
  ├─→ vehicle_model (YOLOv11s COCO, imgsz=1280) → 车辆 bbox
  │                                                   │
  │                                    置信度过滤 (--vehicle_conf 0.35)
  │                                                   │
  │                                    ByteTrack 跟踪 (真实 FPS)
  │                                                   │
  │                                    越线判断 + 计数
  │
  ├─→ plate_model (plate_best.pt, imgsz=1920) → 车牌 bbox (全帧)
  │                                                   │
  └─→ IOU 匹配: plate ∈ vehicle → track_id              │
       │                                               │
       每 track 保留最大车牌帧 ←─────────────────────────┘
       │
       越线时:
         ① 透视矫正 (warpPerspective 梯形→矩形)
         ② CLAHE 增强
         ③ PaddleOCR 识别
         ④ 格式校验（强制省份简称前缀）
         ⑤ HSV 颜色分类 → 车牌号 + 颜色
```

> v2.7 删除了旧的「下 1/3 裁剪 OCR」兜底方案，该方案是假车牌输出的根源（车身贴纸/广告文字被当成车牌）。

运行：

```bash
cd /root/autodl-tmp/traffic_project
conda activate traffic
python deploy/infer.py --video traffic.mp4
```

关键参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--video` | `traffic.mp4` | 输入视频路径 |
| `--vehicle_model` | `yolo11s.pt` | 车辆检测模型（small 精度高于 nano） |
| `--plate_model` | `models/plate_best.pt` | 车牌检测模型 |
| `--line_y` | `0` | 横截线 y 坐标（0=自动按画面53%） |
| `--vehicle_conf` | `0.35` | 车辆检测置信度阈值 |
| `--imgsz` | `1280` | 车辆检测输入尺寸 |
| `--plate_imgsz` | `1920` | 车牌检测输入尺寸（4K 视频推荐 1920+） |
| `--plate_every` | `1` | 每 N 帧检测一次车牌（1=逐帧） |
| `--output` | `results/output.mp4` | 输出视频路径 |

结果输出到 `results/output.mp4`。

------

## 第十二步：OCR 识别模型微调（v2.9，训练中）

### 12.1 问题诊断

v2.8 推理：车辆检测+计数✅ | 字母数字识别勉强可用 | **省份汉字近乎全部 `????`**

根因是**域偏移（Domain Shift）**：PP-OCRv4 通用模型训练数据为自然场景印刷/手写体，缺少蓝底白字车牌专项数据。车牌字体、反光、倾斜角度构成特有分布，通用模型泛化不足。

### 12.2 数据集

| 项目 | 说明 |
|------|------|
| 来源 | CCPD `ccpd_base_plate` 子集 |
| 数量 | **78,896** 张纯车牌裁剪图 |
| 总大小 | 1.4 GB |
| 格式 | JPEG，文件名即车牌号（如 `川A00F87.jpg`） |
| 字符集 | **65 个**（31 省份简称 + 24 字母 + 10 数字） |
| 长度 | 全部 9 位等长 |

### 12.3 数据准备

```bash
cd /root/autodl-tmp/traffic_project
python scripts/prepare_ocr_data.py --src ccpd/ccpd_base_plate --dst dataset/ocr_rec
```

输出结构：
```text
dataset/ocr_rec/
├── images/              # 软链接
├── train.txt            # 69,428 条（88%） 格式: images/xxx.jpg<TAB>车牌号
├── val.txt              # 9,468 条（12%）
└── plate_dict.txt       # 65 个字符，每行一个
```

### 12.4 架构设计

```
SVTR_LCNet (PP-OCRv4)
    │
    ├─ Backbone: PPLCNetV3 (scale=0.95)
    │
    └─ MultiHead
         ├─ CTCHead (定长序列解码)
         │    └─ SVTR Neck (depth=2, dims=120)
         └─ SARHead (注意力机制，抗扭曲)
              └─ enc_dim=120, max_text_length=9

字典: 6625 类(通用) → 65 类(车牌专用)
Loss: CTCLoss + SARLoss 多头联合
```

> 训练日志中 `The shape of head.ctc_head.fc.weight [120, 66] not matched with [120, 6625]` 是**正常现象**——模型成功将分类头从通用 6625 切换为车牌 66 类，预训练权重中不匹配层自动跳过。

### 12.5 踩坑全记录

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | numpy ABI 不匹配 → cv2/Paddle 全崩 | `pip install albumentations` 自动拉 numpy 2.x | `pip install "numpy==1.26.4" --force-reinstall --no-deps` |
| 2 | 系统盘 78% | /tmp 缓存 + pip 缓存 + 残留 screen | 删除 /tmp/PaddleOCR, `pip cache purge`, `screen -wipe` |
| 3 | /tmp/PaddleOCR 不稳定 | 临时目录非持久化 | 克隆到项目目录 `traffic_project/PaddleOCR` |
| 4 | C++ segfault（最致命） | batch=128 + workers=8 → Docker 共享内存爆仓 + 坏图 | **batch=32, workers=2** |
| 5 | "all input arrays must have the same shape" | 车牌图片尺寸不统一，大批次张量堆叠失败 | batch=32 保证维度对齐 |
| 6 | best_accuracy.pdparams 不存在 | 训练未跑完就尝试导出 | 等完整 epoch 跑完再 export |

### 12.6 最终稳定训练流程

```bash
# 每次训练前执行
source /root/miniconda3/etc/profile.d/conda.sh
conda activate traffic
pip install "numpy==1.26.4" --force-reinstall --no-deps -q
export OMP_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=0

# 启动训练
cd /root/autodl-tmp/traffic_project/PaddleOCR
screen -S train_ocr
python tools/train.py -c configs/rec/plate_rec.yml
# Ctrl+A+D 挂起（不终止训练）
# screen -r train_ocr 恢复查看
# screen -D -r 会话ID 强制接管冲突会话
```

### 12.7 训练完成后

**导出推理模型：**
```bash
python tools/export_model.py -c configs/rec/plate_rec.yml \
  -o Global.pretrained_model=/root/autodl-tmp/traffic_project/output/plate_rec/best_accuracy \
  Global.save_inference_dir=/root/autodl-tmp/traffic_project/output/plate_rec_infer
```

**替换项目 OCR 权重：** 修改 `ocr/plate_ocr.py`，PaddleOCR 初始化指向微调模型：
```python
self.ocr = PaddleOCR(
    use_angle_cls=True, lang='ch', show_log=False, use_gpu=True,
    rec_model_dir='/root/autodl-tmp/traffic_project/output/plate_rec_infer'
)
```

**复测验证：**
```bash
cd /root/autodl-tmp/traffic_project
python deploy/infer.py --video traffic.mp4 --output results/output_v2.9.mp4
```

### 12.8 经验总结

1. **绝对不要裸装 pip 包**：`pip install xxx --no-deps`，防止依赖链炸环境
2. **训练 batch 不能照搬官方**：真实场景车牌尺寸不统一，batch=32 最稳
3. **工程不能放 /tmp**：临时目录不稳定。所有项目固定放 `autodl-tmp` 数据盘
4. **屏幕会话不要重复创建**：用 `screen -ls` 检查，用 `screen -r` 恢复已有会话
5. **预训练模型的 shape mismatch 警告是正常的**：字典替换必然导致分类头维度变化，无需处理

---

## 第十一步：项目最终结构

以下为 AutoDL 云端实际目录结构（`tree -L 3` 输出）：

```text
traffic_project/                       # 项目根目录 (/root/autodl-tmp/traffic_project)
│
├── check_dependencies.py              # 依赖检查脚本
├── data.yaml                          # YOLO 训练数据配置
├── requirements.txt                   # Python 依赖列表
├── traffic.mp4                        # 测试视频 (4K, 451MB)
├── yolo11s.pt                         # 车辆检测模型 (COCO small，推理时使用)
├── yolo11n.pt                         # 车辆检测模型 (COCO nano，备选)
│
├── color/                             # 颜色识别模块
│   ├── __init__.py
│   └── plate_color.py                 # HSV 颜色分类（蓝/绿/黄/其他）
│
├── ocr/                               # 车牌识别模块
│   ├── __init__.py
│   └── plate_ocr.py                   # PaddleOCR 封装 + 预处理 + 车牌区域定位
│
├── tracking/                          # 跟踪与计数模块
│   ├── __init__.py
│   ├── tracker.py                     # ByteTrack 封装（真实 FPS 传入）
│   └── counter.py                     # 越线判断 + 双向车流计数 + 位移过滤
│
├── deploy/                            # 部署推理
│   └── infer.py                       # v2.8 主推理管线（全帧双检测+缓存重试+198MB模型）
│
├── train/                             # 训练模块
│   ├── train.py                       # YOLOv11 车牌检测训练脚本
│   ├── ocr_rec_config.yml            # PaddleOCR rec 微调配置 (batch=32,workers=2)
│   └── train_ocr.py                  # v2.9 训练入口（调用 PaddleOCR tools/train.py）
│
├── scripts/                           # 工具脚本
│   ├── convert_ccpd.py                # CCPD2019 文件名标注 → YOLO .txt 格式
│   ├── split_dataset.py               # 训练/验证集划分
│   ├── extract_frames.py              # 视频抽帧
│   ├── prepare_ocr_data.py            # OCR 微调数据准备（v2.9 新增）
│   ├── test_ocr.py                    # PaddleOCR 返回格式测试
│   └── test_pipeline.py               # 全流程测试（OCR/颜色/视频抽帧）
│
├── scripts/                           # 工具脚本
│   ├── convert_ccpd.py                # CCPD2019 文件名标注 → YOLO .txt 格式
│   ├── split_dataset.py               # 训练/验证集划分
│   ├── extract_frames.py              # 视频抽帧
│   ├── test_ocr.py                    # PaddleOCR 返回格式测试
│   └── test_pipeline.py               # 全流程测试（OCR/颜色/视频抽帧）
│
├── PaddleOCR/                         # PaddleOCR 完整仓库 v2.9（含训练工具+配置）
│   └── configs/rec/plate_rec.yml     # 车牌微调配置 (SVTR_LCNet, batch=32)
├── pretrain_models/                   # 预训练权重
│   └── ch_PP-OCRv4_rec_train/        # PP-OCRv4 rec 学生模型预训练权重
├── ccpd/                              # OCR 微调数据集
│   └── ccpd_base_plate/              # 78,896 张纯车牌图片
├── output/                            # 训练产出
│   ├── plate_rec/                    # OCR 微调 checkpoint
│   └── plate_rec_infer/              # OCR 微调导出推理模型
│
├── models/                            # 模型权重（训练产出）
│   └── plate_best.pt                  # 车牌检测最优权重（train-6 产出）
│
├── dataset/                           # 数据集
│   ├── images/
│   │   ├── train/                     # 训练集图片 (~17000张)
│   │   └── val/                       # 验证集图片 (~3000张)
│   ├── labels/
│   │   ├── train/                     # 训练集标签 (YOLO .txt)
│   │   └── val/                       # 验证集标签
│   └── ccpd_yolo/                     # CCPD2019 全量转换数据（中间产物）
│       ├── images/
│       └── labels/
│
├── runs/                              # 训练运行记录
│   └── detect/
│       ├── train/                     # 第1次训练
│       ├── train-2/                   # 第2次训练
│       ├── train-3/                   # 第3次训练
│       ├── train-4/                   # 第4次训练
│       ├── train-5/                   # 第5次训练
│       └── train-6/                   # 第6次训练 → 产出 models/plate_best.pt
│
└── results/                           # 推理输出
    └── output.mp4                     # 带标注框+车牌+计数的结果视频
```

> **注意**：`yolo11s.pt` 和 `yolo11n.pt` 是 ultralytics 首次运行时自动下载的 COCO 预训练权重，无需手动上传。`runs/detect/` 下的多次训练记录保留以对比不同轮次效果。

------

## 完成后的提交清单

| 材料 | 说明 |
|------|------|
| 实验报告 | 含需求分析、方案设计、训练过程、评估结果 |
| 项目完整代码 | 即此 `traffic_project` 目录，含训练和部署说明 |
| 项目汇报PPT | 展示系统架构、核心算法、演示效果截图 |

------

## 数据说明

数据集已标注好，无需手动标注。整个项目的核心工作量分布如下：

```text
工作量分布：
训练调试 (35%)  >>  管线串联 (30%)  >>  OCR调优 (15%)  >>  结果渲染 (10%)  >>  文档/PPT (10%)
```

| 模型 | 数据来源 | 是否需训练 | 说明 |
|------|---------|-----------|------|
| 车辆检测 YOLOv11 | COCO 预训练权重 | ❌ 无需训练 | car/bus/truck 原生支持 |
| 车牌检测 YOLOv11 | CCPD2019 训练产出 | ✅ 已完成 | 100轮，mAP50-95 0.98 |
| 车牌 OCR | PaddleOCR 2.7.3 | ❌ 无需训练 | PP-OCRv4 中文模型 |
| 车牌颜色 | OpenCV HSV 规则 | ❌ 无需训练 | 纯规则，见第九步 |
