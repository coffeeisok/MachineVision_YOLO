"""
scripts/prepare_ocr_data.py
准备 PaddleOCR rec 模型微调数据。

输入: ccpd_base_plate/ 目录 (7.8万张纯车牌图片，文件名=车牌号)
输出:
  dataset/ocr_rec/train.txt   (格式: image_path<TAB>label)
  dataset/ocr_rec/val.txt
  dataset/ocr_rec/images/     (软链接到原始图片)

用法:
  python scripts/prepare_ocr_data.py --src ccpd/ccpd_base_plate --dst dataset/ocr_rec
"""
import os
import sys
import random
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(src_dir: str, dst_dir: str, val_ratio: float = 0.12):
    # 收集所有图片
    images = [f for f in os.listdir(src_dir) if f.lower().endswith('.jpg')]
    label_map = {}
    for fname in images:
        plate_no = os.path.splitext(fname)[0]  # 文件名即标签，如 "川A00F87"
        if len(plate_no) >= 6:
            label_map[fname] = plate_no

    print(f"有效图片: {len(label_map)} / {len(images)}")

    # 打乱并划分
    items = list(label_map.items())
    random.seed(42)
    random.shuffle(items)

    split = int(len(items) * (1 - val_ratio))
    train_items = items[:split]
    val_items = items[split:]

    # 创建目录
    img_dst = os.path.join(dst_dir, "images")
    os.makedirs(img_dst, exist_ok=True)

    # 写标注文件 + 创建软链接
    for name, txt_path in [("train", os.path.join(dst_dir, "train.txt")),
                            ("val", os.path.join(dst_dir, "val.txt"))]:
        subset = train_items if name == "train" else val_items
        with open(txt_path, "w", encoding="utf-8") as f:
            for fname, label in sorted(subset):
                src = os.path.abspath(os.path.join(src_dir, fname))
                dst = os.path.join(img_dst, fname)
                if not os.path.exists(dst):
                    os.symlink(src, dst)
                # PaddleOCR 格式: 相对路径<TAB>标签
                rel_path = os.path.join("images", fname)
                f.write(f"{rel_path}\t{label}\n")

        print(f"{name}: {len(subset)} 条 → {txt_path}")

    # 生成字典文件 (供 PaddleOCR 训练配置使用)
    chars = set()
    for _, label in label_map.items():
        chars.update(label)
    chars = sorted(chars)

    dict_path = os.path.join(dst_dir, "plate_dict.txt")
    with open(dict_path, "w", encoding="utf-8") as f:
        for c in chars:
            f.write(c + "\n")

    print(f"字典: {len(chars)} 个字符 → {dict_path}")
    print(f"字符集: {''.join(chars)}")
    print("\n✅ 数据准备完成!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=os.path.join(PROJECT_ROOT, "ccpd", "ccpd_base_plate"))
    parser.add_argument("--dst", default=os.path.join(PROJECT_ROOT, "dataset", "ocr_rec"))
    parser.add_argument("--val_ratio", type=float, default=0.12)
    args = parser.parse_args()

    if not os.path.isdir(args.src):
        print(f"❌ 源目录不存在: {args.src}")
        sys.exit(1)

    main(args.src, args.dst, args.val_ratio)
