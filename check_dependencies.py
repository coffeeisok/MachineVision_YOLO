# check_dependencies.py
import sys

print("Python version:", sys.version)

# torch
try:
    import torch
    print("torch imported successfully")
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
except Exception as e:
    print("torch import failed:", e)

# ultralytics YOLO
try:
    from ultralytics import YOLO
    print("ultralytics YOLO imported successfully")
    # 测试模型加载
    model = YOLO("yolo11n.pt")
    print("YOLOv11 model loaded successfully")
except Exception as e:
    print("YOLO import/load failed:", e)

# opencv
try:
    import cv2
    print("opencv imported successfully, version:", cv2.__version__)
except Exception as e:
    print("opencv import failed:", e)

# supervision
try:
    import supervision as sv
    print("supervision imported successfully")
except Exception as e:
    print("supervision import failed:", e)

# paddleocr + paddlepaddle
try:
    import paddleocr
    import paddle
    print("paddleocr and paddle imported successfully")
    print("paddle version:", paddle.__version__)
except Exception as e:
    print("paddleocr/paddle import failed:", e)

# matplotlib
try:
    import matplotlib
    print("matplotlib imported successfully, version:", matplotlib.__version__)
except Exception as e:
    print("matplotlib import failed:", e)

# pandas
try:
    import pandas as pd
    print("pandas imported successfully, version:", pd.__version__)
except Exception as e:
    print("pandas import failed:", e)