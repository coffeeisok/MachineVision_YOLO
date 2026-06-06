"""
scripts/convert_ccpd.py
将 CCPD2019 数据集（文件名编码标注）转换为 YOLO 格式。

CCPD2019 文件名格式：
  025-95_113-154&383_386&473-386&473_177&454_154&383_363&402-0_0_22_27_27_33_16-37-15.jpg
   ^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^ ^^^^^^
   面积比  车牌四角坐标(x1,y1&x2,y2-x3,y3&x4,y4...)            其他信息          亮度/模糊度

输出：
  每张图片 → 复制到 output/images/
  每张图片 → 生成 output/labels/同名.txt（YOLO 格式：plate 类别 + bbox）
"""
import os
import cv2
import shutil
import argparse
from pathlib import Path


def parse_ccpd_filename(filename: str):
    """
    解析 CCPD2019 文件名，提取车牌四角坐标。

    Returns:
        corners: [(x1,y1), (x2,y2), (x3,y3), (x4,y4)] 或 None
    """
    stem = Path(filename).stem
    parts = stem.split("-")

    if len(parts) < 3:
        return None

    # CCPD2019 文件名: area-tilt-bbox-vertices-lp_info-brightness-blur.jpg
    # vertices 在第4段（索引3），格式: x1&y1_x2&y2_x3&y3_x4&y4
    coord_str = parts[3]  # 如 "386&473_177&454_154&383_363&402"

    # 先按 _ 拆分得到 4 个 vertex，再按 & 拆分得到 (x, y)
    vertex_strings = coord_str.split("_")
    if len(vertex_strings) < 4:
        return None

    corners = []
    for vs in vertex_strings[:4]:
        try:
            x, y = vs.split("&")
            corners.append((int(x), int(y)))
        except ValueError:
            return None

    return corners


def corners_to_yolo_bbox(corners: list, img_w: int, img_h: int):
    """
    将四角坐标转为 YOLO 格式 (class_id x_center y_center width height)，归一化。

    车牌四个角通常构成四边形，取 min/max 得到轴对齐 bbox。
    """
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    bbox_w = x_max - x_min
    bbox_h = y_max - y_min
    x_center = (x_min + x_max) / 2.0
    y_center = (y_min + y_max) / 2.0

    # 归一化
    x_center /= img_w
    y_center /= img_h
    bbox_w /= img_w
    bbox_h /= img_h

    # 裁剪到 [0,1]
    x_center = max(0, min(1, x_center))
    y_center = max(0, min(1, y_center))
    bbox_w = max(0, min(1, bbox_w))
    bbox_h = max(0, min(1, bbox_h))

    return x_center, y_center, bbox_w, bbox_h


def convert_ccpd(source_dir: str, output_dir: str, plate_class_id: int = 0):
    """
    遍历 CCPD2019 子目录，转换所有图片为 YOLO 格式。

    Args:
        source_dir: CCPD2019 根目录（含 ccpd_base, ccpd_challenge 等子目录）
        output_dir: 输出目录（生成 images/ 和 labels/）
    """
    source = Path(source_dir)
    output = Path(output_dir)
    (output / "images").mkdir(parents=True, exist_ok=True)
    (output / "labels").mkdir(parents=True, exist_ok=True)

    total = 0
    success = 0

    for subdir in sorted(source.iterdir()):
        if not subdir.is_dir() or not subdir.name.startswith("ccpd"):
            continue

        for img_file in sorted(subdir.glob("*.jpg")):
            total += 1

            corners = parse_ccpd_filename(img_file.name)
            if corners is None:
                continue

            # 读图片获取尺寸
            img = cv2.imread(str(img_file))
            if img is None:
                continue
            img_h, img_w = img.shape[:2]

            # 转换为 YOLO bbox
            x_c, y_c, bw, bh = corners_to_yolo_bbox(corners, img_w, img_h)

            # 复制图片
            shutil.copy2(img_file, output / "images" / img_file.name)

            # 写标签
            label_path = output / "labels" / f"{img_file.stem}.txt"
            with open(label_path, "w") as f:
                f.write(f"{plate_class_id} {x_c:.6f} {y_c:.6f} {bw:.6f} {bh:.6f}\n")

            success += 1

    print(f"转换完成：{success}/{total} 张图片")


if __name__ == "__main__":
    # 项目根目录 = scripts/ 的上一级
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(description="CCPD2019 → YOLO 格式转换")
    parser.add_argument("--source", default=None,
                        help="CCPD2019 根目录路径（默认自动查找）")
    parser.add_argument("--output", default=os.path.join(PROJECT_ROOT, "dataset", "ccpd_yolo"),
                        help="输出目录")
    parser.add_argument("--class_id", type=int, default=0,
                        help="车牌类别 ID")
    args = parser.parse_args()

    # 自动查找 CCPD2019
    if args.source is None:
        candidates = [
            "/root/autodl-tmp/CCPD2019",
            os.path.join(PROJECT_ROOT, "..", "CCPD2019"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                args.source = c
                break
        if args.source is None:
            print("❌ 未找到 CCPD2019 目录，请用 --source 指定路径")
            print(f"   尝试过的路径: {candidates}")
            exit(1)

    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"源目录:     {args.source}")
    print(f"输出目录:   {args.output}")
    convert_ccpd(args.source, args.output, args.class_id)
    print(f"\n下一步: python split_dataset.py")
