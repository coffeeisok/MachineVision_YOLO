"""
scripts/convert_ccpd.py — CCPD2019 → YOLO 格式转换 (v3.0)
带进度条 + 强制覆盖 + ETA
"""
import os, cv2, shutil, argparse, time
from pathlib import Path


def parse_ccpd_filename(filename):
    stem = Path(filename).stem
    parts = stem.split("-")
    if len(parts) < 3:
        return None
    coord_str = parts[3]
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


def corners_to_yolo_bbox(corners, img_w, img_h):
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    bw, bh = x_max - x_min, y_max - y_min
    xc = ((x_min + x_max) / 2.0) / img_w
    yc = ((y_min + y_max) / 2.0) / img_h
    bw /= img_w
    bh /= img_h
    return max(0, min(1, xc)), max(0, min(1, yc)), max(0, min(1, bw)), max(0, min(1, bh))


def convert_ccpd(source_dir, output_dir, plate_class_id=0):
    source = Path(source_dir)
    output = Path(output_dir)
    (output / "images").mkdir(parents=True, exist_ok=True)
    (output / "labels").mkdir(parents=True, exist_ok=True)

    # 收集所有子目录
    subdirs = sorted(
        d for d in source.iterdir() if d.is_dir() and d.name.startswith("ccpd")
    )

    # 统计总数
    total = 0
    for subdir in subdirs:
        total += len(list(subdir.glob("*.jpg")))
    print(f"找到 {len(subdirs)} 个子目录，共 {total} 张图片\n")

    success = 0
    processed = 0
    start_time = time.time()

    for subdir in subdirs:
        print(f"[{subdir.name}] ({total} total)")
        for img_file in sorted(subdir.glob("*.jpg")):
            processed += 1
            corners = parse_ccpd_filename(img_file.name)

            if corners is None:
                continue

            img = cv2.imread(str(img_file))
            if img is None:
                continue

            h, w = img.shape[:2]
            xc, yc, bw, bh = corners_to_yolo_bbox(corners, w, h)

            # 强制覆盖
            dst_img = output / "images" / img_file.name
            dst_label = output / "labels" / f"{img_file.stem}.txt"
            shutil.copy2(img_file, dst_img)
            with open(dst_label, "w") as f:
                f.write(f"{plate_class_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")
            success += 1

            # 每 1000 张显示进度
            if processed % 1000 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (total - processed) / rate if rate > 0 else 0
                pct = processed / total * 100
                print(
                    f"  {processed}/{total} ({pct:.1f}%) | "
                    f"成功:{success} | {rate:.0f} img/s | "
                    f"预计剩余:{eta/60:.1f}min"
                )

    elapsed = time.time() - start_time
    print(f"\n✅ 完成！{success}/{total} 张 | 耗时 {elapsed/60:.1f} 分钟")


if __name__ == "__main__":
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description="CCPD2019 -> YOLO")
    parser.add_argument("--source", default="/root/autodl-tmp/CCPD2019")
    parser.add_argument("--output", default=os.path.join(PROJECT_ROOT, "dataset", "ccpd_yolo"))
    parser.add_argument("--class_id", type=int, default=0)
    args = parser.parse_args()
    print(f"源: {args.source}")
    print(f"输出: {args.output}\n")
    convert_ccpd(args.source, args.output, args.class_id)
