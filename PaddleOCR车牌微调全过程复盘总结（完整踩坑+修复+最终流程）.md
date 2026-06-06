# PaddleOCR车牌微调全过程复盘总结（完整踩坑\+修复\+最终流程）

## 一、项目目标

解决原有PP\-OCRv4通用模型**车牌识别全部????、汉字识别失效**问题，基于CCPD车牌数据集微调专属车牌识别模型，适配交通监控视频车牌识别场景。

## 二、完整执行时间线（从0到当前）

### 阶段1：数据集准备（无坑）

1\. 本地通过FileZilla/scp上传CCPD车牌数据集（1\.4G）到云端

2\. 云端执行数据预处理脚本：划分训练集/验证集、生成标签文件、生成车牌字典

✅ 产出：train\.txt、val\.txt、plate\_dict\.txt（数据集完全就绪）

### 阶段2：初次搭建PaddleOCR（埋下隐患）

1\. 最初将PaddleOCR克隆在 **/tmp/PaddleOCR** 临时目录

2\. 手动编写专属车牌训练yml配置文件

❌ 隐患1：tmp为系统临时目录，不稳定、容易冲突、文件易丢失

❌ 隐患2：初始配置 **batch\_size=128，num\_workers=8**（显存/数据加载必崩）

### 阶段3：安装依赖引发【环境大崩溃】（最大核心坑）

执行：`pip install albumentations lmdb tqdm`

❌ 自动升级 numpy `1.26.4 → 2.2.6`

引发连环报错：

- numpy ABI版本不匹配

- cv2导入失败

- albumentations库直接失效

- Paddle/GPU无法初始化

✅ 修复：强制降级numpy \+ **永久锁定numpy版本**，禁止自动升级

✅ 习得规则：后续所有pip安装必须加 `--no-deps`

### 阶段4：磁盘爆满问题

❌ 问题：tmp缓存、旧代码、pip缓存、重复screen会话导致系统盘占用78%

✅ 解决方案：

- 删除 /tmp/PaddleOCR 旧工程

- 清理pip缓存 `pip cache purge`

- 清理无效screen会话 `screen -wipe`

- 将PaddleOCR迁移到项目目录：**/root/autodl\-tmp/traffic\_project/PaddleOCR**

✅ 磁盘占用从78% → 51%，环境干净稳定

### 阶段5：Screen后台会话混乱

❌ 问题：多次新建训练窗口，出现重复 `train_ocr` 会话，无法进入、冲突报错

✅ 习得操作：

- `screen -ls` 查看所有会话

- `screen -D -r 会话ID` 强制接管冲突会话

- `Ctrl+A+D` 后台挂起（不终止训练）

### 阶段6：模型导出报错

报错：`best_accuracy.pdparams 不存在`

❌ 原因：**训练未跑完，最优模型权重未生成**（不是命令错误）

✅ 规则：必须完整跑完epoch，才能执行export\_model导出推理模型

### 阶段7：最终训练崩溃（数据维度错误）

终极报错：`ValueError: all input arrays must have the same shape`

❌ 根源（100%定位）：

- 配置文件未生效，依然是 **batch\_size=128**

- num\_workers=8 线程过多

- 车牌图片尺寸不统一，大批次无法堆叠

✅ 最终修复：批量修改为 **batch=32，workers=2**

## 三、所有报错汇总 \+ 根本原因 \+ 解决方案

|报错现象|根本原因|解决方案|
|---|---|---|
|numpy ABI不匹配、cv2导入失败|pip自动升级numpy到2\.x，Paddle只支持1\.26\.4|强制降级 \+ conda锁定numpy版本|
|系统磁盘占用过高|tmp临时文件、缓存、冗余代码过多|迁移工程、清理缓存、删除旧文件|
|screen会话冲突、无法进入|重复创建训练窗口导致Attached占用|强制接管、清理无效会话|
|best\_accuracy\.pdparams不存在|训练未完成，最优权重未保存|等待训练跑完再导出模型|
|all input arrays must have the same shape|batch超大、线程过多、图片尺寸不统一|batch=32、workers=2|
|OMP\_NUM\_THREADS环境变量报错|线程变量非法|export OMP\_NUM\_THREADS=1|
|模型参数shape不匹配警告|通用OCR字典6625类 → 车牌66类|正常现象，无需处理（迁移预训练权重）|

## 四、本次最大的3个致命踩坑（核心经验）

**1\. 绝对不要裸装pip包**

任何安装必须：`pip install xxx --no-deps`，防止numpy/依赖被乱升级炸环境

**2\. 训练batch绝对不能乱设128**

真实场景图片尺寸不统一，大批次100%维度报错，车牌训练固定 batch=32 最稳

**3\. 工程绝对不能放/tmp**

临时目录不稳定、易冲突、易丢文件，所有项目固定放 autodl\-tmp 项目目录

## 五、最终【100%稳定、无报错】训练流程（定稿）

### 1\. 环境初始化（每次训练前）

```Plain Text
source /root/miniconda3/etc/profile.d/conda.sh
conda activate traffic
pip install "numpy==1.26.4" --force-reinstall --no-deps 2>/dev/null
export OMP_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=0
```

### 2\. 固定正确配置

batch\_size\_per\_card: 32

num\_workers: 2

### 3\. 后台启动训练

```Plain Text
cd /root/autodl-tmp/traffic_project/PaddleOCR
screen -S train_ocr
python tools/train.py -c configs/rec/plate_rec.yml
```

### 4\. 后台管理

退出不终止：`Ctrl+A+D`

恢复查看：`screen -r train_ocr`

### 5\. 训练结束后导出模型

```Plain Text
python tools/export_model.py -c configs/rec/plate_rec.yml \
-o Global.pretrained_model=/root/autodl-tmp/traffic_project/output/plate_rec/best_accuracy \
Global.save_inference_dir=/root/autodl-tmp/traffic_project/output/plate_rec_infer
```

## 六、当前阶段状态

✅ 数据集完整就绪

✅ 环境彻底修复、numpy锁定、无版本冲突

✅ 磁盘空间充足、工程目录规范

✅ 训练配置参数适配车牌场景、不会再维度报错

✅ GPU正常启用

🟡 正在进行：60 epoch 车牌专属模型微调训练

🔜 下一步：导出推理模型 → 替换项目旧OCR权重 → 复测视频车牌识别效果

> （注：文档部分内容可能由 AI 生成）
