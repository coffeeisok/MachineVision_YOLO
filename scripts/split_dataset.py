"""
scripts/split_dataset.py
将 YOLO 格式标注数据按比例划分为训练集和验证集。

CCPD2019 划分策略：
  ccpd_base 有 ~96k 张，全量训练没必要（耗时长、收益递减）。
  建议 --max_samples 20000，从 ccpd_base 中随机采样后 85/15 划分。
  其余子集（challenge/db/fn/rotate/tilt/weather）可留作测试或按需混入 val 做鲁棒性验证。
"""
import os
import shutil
import random
import argparse
from pathlib import Path


def split_dataset(
    source_dir: str,
    target_dir: str,
    train_ratio: float = 0.85,
    max_samples: int = 0,
    seed: int = 42,
):
    random.seed(seed)

    source = Path(source_dir)
    target = Path(target_dir)

    # 源目录结构：source/images/*.jpg + source/labels/*.txt
    src_images = source / "images"
    src_labels = source / "labels"

    if not src_images.exists():
        print(f"❌ 源图片目录不存在: {src_images}")
        print("   提示：先运行 convert_ccpd.py 生成 ccpd_yolo 目录")
        return

    # 收集所有带标签的图片
    image_files = []
    for f in sorted(src_images.iterdir()):
        if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
            label_file = src_labels / f"{f.stem}.txt"
            if label_file.exists():
                image_files.append(f)

    if not image_files:
        print(f"❌ 未找到带标签的图片！请确认 {src_images}/ 下有 .jpg，{src_labels}/ 下有对应的 .txt")
        return

    total = len(image_files)

    # 可选：限制总采样数（随机采样）
    if max_samples > 0 and max_samples < total:
        image_files = random.sample(image_files, max_samples)
        print(f"全量: {total} → 采样: {max_samples} 张")
    else:
        print(f"全量图片: {total} 张")

    # 划分
    split_idx = int(len(image_files) * train_ratio)
    train_files = image_files[:split_idx]
    val_files = image_files[split_idx:]

    print(f"训练集:   {len(train_files)} 张 ({train_ratio*100:.0f}%)")
    print(f"验证集:   {len(val_files)} 张 ({(1-train_ratio)*100:.0f}%)")

    # 创建目录
    for split in ["train", "val"]:
        (target / "images" / split).mkdir(parents=True, exist_ok=True)
        (target / "labels" / split).mkdir(parents=True, exist_ok=True)

    # 复制文件
    def copy_files(files, split_name):
        for i, img in enumerate(files):
            label = src_labels / f"{img.stem}.txt"
            shutil.copy2(img, target / "images" / split_name / img.name)
            shutil.copy2(label, target / "labels" / split_name / f"{img.stem}.txt")
            if (i + 1) % 2000 == 0:
                print(f"  {split_name}: {i+1}/{len(files)}...")

    copy_files(train_files, "train")
    copy_files(val_files, "val")

    print(f"✅ 划分完成 → {target}/images/{{train,val}} + {target}/labels/{{train,val}}")


if __name__ == "__main__":
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(description="划分训练/验证集")
    parser.add_argument("--source", default=os.path.join(PROJECT_ROOT, "dataset", "ccpd_yolo"),
                        help="标注数据源目录（含 images/ 和 labels/）")
    parser.add_argument("--target", default=os.path.join(PROJECT_ROOT, "dataset"),
                        help="输出目录（生成 images/train|val + labels/train|val）")
    parser.add_argument("--ratio", type=float, default=0.85,
                        help="训练集占比 (默认 0.85)")
    parser.add_argument("--max_samples", type=int, default=20000,
                        help="最多采样张数 (0=不限制; CCPD 建议 20000)")
    args = parser.parse_args()

    split_dataset(args.source, args.target, args.ratio, args.max_samples)
