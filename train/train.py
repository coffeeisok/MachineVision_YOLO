"""
train/train.py
YOLOv11 车牌检测模型训练脚本 (CCPD2019)。
"""
from ultralytics import YOLO
import argparse


def main():
    parser = argparse.ArgumentParser(description="训练 YOLOv11 车牌检测模型")
    parser.add_argument("--model", default="yolo11n.pt", help="预训练权重")
    parser.add_argument("--data", default="data.yaml", help="数据配置文件")
    parser.add_argument("--epochs", type=int, default=100, help="训练轮数")
    parser.add_argument("--imgsz", type=int, default=640, help="输入尺寸")
    parser.add_argument("--batch", type=int, default=64, help="批次大小 (5090可到128)")
    parser.add_argument("--workers", type=int, default=12, help="数据加载线程数")
    parser.add_argument("--device", default="0", help="GPU 设备")
    args = parser.parse_args()

    model = YOLO(args.model)

    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=args.device,
        patience=15,
        save=True,
        save_period=10,
        cache=True,          # 数据集缓存到 RAM（20k 张完全装得下）
    )

    print("\n✅ 训练完成！")
    print("   最佳权重: runs/detect/train/weights/best.pt")
    print("   请复制到 models/plate_best.pt 供推理使用")


if __name__ == "__main__":
    main()
