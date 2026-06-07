#!/usr/bin/env python3
"""
生成实验报告剩余素材：素材-01 + 素材-04 + 素材-12
输出路径: docs/materials/
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os, random, glob

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'materials')
os.makedirs(OUTPUT, exist_ok=True)

# ============================================================
# 素材-01: 技术演进时间线图
# ============================================================
def generate_timeline():
    print("生成 素材-01: 技术演进时间线图...")

    # 中文字体
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti SC', 'PingFang SC', 'SimHei', 'Noto Sans CJK SC']
    plt.rcParams['axes.unicode_minus'] = False

    fig, ax = plt.subplots(figsize=(16, 5))
    ax.set_xlim(2009, 2026)
    ax.set_ylim(0, 5)
    ax.axis('off')

    # 时间段背景
    phases = [
        (2010, 2014, '#FFF3CD', '传统方法时代'),
        (2014, 2018, '#D4EDDA', '两阶段检测时代'),
        (2018, 2023, '#CCE5FF', '单阶段检测时代'),
        (2023, 2026, '#E8DAEF', '大模型时代'),
    ]
    for x1, x2, color, label in phases:
        rect = FancyBboxPatch((x1, 0.3), x2-x1, 4.3, boxstyle="round,pad=0.1",
                              facecolor=color, edgecolor='gray', alpha=0.4, linewidth=0.5)
        ax.add_patch(rect)
        ax.text((x1+x2)/2, 4.55, label, ha='center', va='center', fontsize=11, fontweight='bold', color='#555')

    # 时间轴线
    ax.plot([2010, 2025], [3.8, 3.8], 'k-', linewidth=1.5, color='#333')
    for y_pos in [0.5, 1.3, 2.1, 2.9, 3.8]:
        pass  # keep main line only

    # 里程碑事件数据: (年份, y_pos, 标签, 描述, 颜色)
    milestones = [
        (2010, 3.0, 'HOG+SVM\n+卡尔曼滤波', '精度~70%\n速度~5FPS', '#E74C3C'),
        (2014, 2.0, 'Faster R-CNN\n两阶段检测', '精度~85%\n速度~5FPS', '#E67E22'),
        (2016, 1.0, 'YOLO v1\n单阶段检测', '精度~75%\n速度~45FPS', '#2ECC71'),
        (2018, 2.5, 'YOLOv3\n多尺度检测', '精度~90%\n速度~30FPS', '#27AE60'),
        (2020, 2.0, 'DETR\n端到端Transformer', '去除NMS\n全局感受野', '#8E44AD'),
        (2023, 1.0, 'YOLOv8 ⭐\nAnchor-Free', 'mAP50-95=50.2%\n本项目采用', '#2980B9'),
        (2024, 3.0, 'GPT-4V/SAM\n多模态大模型', '零样本泛化\n延迟>1s', '#9B59B6'),
    ]

    for year, y, tech, desc, color in milestones:
        # 圆点
        ax.plot(year, 3.8, 'o', color=color, markersize=12 if year == 2023 else 8,
                zorder=5, markeredgecolor='white', markeredgewidth=1.5)

        # 竖线
        ax.plot([year, year], [3.8, y], '--', color=color, linewidth=1, alpha=0.6)

        # 技术名称
        bbox_props = dict(boxstyle="round,pad=0.3", facecolor=color, edgecolor='white', alpha=0.9)
        ax.text(year, y-0.15, tech, ha='center', va='top', fontsize=9, fontweight='bold',
                color='white', bbox=bbox_props, zorder=6)

        # 描述文字
        ax.text(year, y-1.0, desc, ha='center', va='top', fontsize=7.5, color='#666')

    # ★ 标注本项目位置
    ax.annotate('★ 本项目\n(YOLOv8m)', xy=(2023, 3.8), xytext=(2023, 0.2),
                ha='center', fontsize=10, fontweight='bold', color='#2980B9',
                arrowprops=dict(arrowstyle='->', color='#2980B9', lw=2))

    # 标题
    ax.text(2017.5, 5.1, '智能交通视觉技术演进 (2010 → 2024)', ha='center', va='center',
            fontsize=16, fontweight='bold', color='#2C3E50')
    ax.text(2017.5, 4.75, '车辆检测与跟踪技术的代际更迭', ha='center', va='center',
            fontsize=11, color='#7F8C8D')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT, '01_技术演进时间线.png'), dpi=200, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("  ✅ 01_技术演进时间线.png 已生成")


# ============================================================
# 素材-04: CCPD2019 3×3 样本网格
# ============================================================
def generate_ccpd_grid():
    print("生成 素材-04: CCPD2019 样本网格...")

    subsets = {
        'ccpd_base': '标准车牌\n(base)',
        'ccpd_challenge': '挑战样本\n(challenge)',
        'ccpd_db': '光照变化\n(db)',
        'ccpd_fn': '远近变化\n(fn)',
        'ccpd_rotate': '旋转倾斜\n(rotate)',
        'ccpd_tilt': '透视变形\n(tilt)',
        'ccpd_weather': '天气变化\n(weather)',
    }

    # 找到 CCPD2019 目录
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'CCPD2019')

    selected_images = []
    labels_for_display = []

    for subset_name, label in subsets.items():
        subset_dir = os.path.join(base_dir, subset_name)
        if os.path.isdir(subset_dir):
            files = os.listdir(subset_dir)[:200]  # 只看前200张，随机选
            if files:
                img_path = os.path.join(subset_dir, random.choice(files))
                selected_images.append(img_path)
                labels_for_display.append(label)
        else:
            print(f"  ⚠️ 子集 {subset_name} 不存在: {subset_dir}")

    # 额外加2张（从base中再选2张不同角度，凑满9张）
    base_dir_full = os.path.join(base_dir, 'ccpd_base')
    if os.path.isdir(base_dir_full):
        extras = random.sample(os.listdir(base_dir_full)[:500], min(2, len(os.listdir(base_dir_full)[:500])))
        for f in extras:
            selected_images.append(os.path.join(base_dir_full, f))
        labels_for_display.append('标准车牌\n(base)')
        labels_for_display.append('标准车牌\n(base)')

    # 确保9张
    selected_images = selected_images[:9]
    labels_for_display = labels_for_display[:9]

    # 创建 3×3 网格
    cell_w, cell_h = 360, 240
    gap = 8
    label_h = 40
    grid_w = cell_w * 3 + gap * 4
    grid_h = (cell_h + label_h) * 3 + gap * 4

    canvas = Image.new('RGB', (grid_w, grid_h), 'white')
    draw = ImageDraw.Draw(canvas)

    # 尝试加载字体
    font_paths = [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    ]
    font = None
    font_small = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 16)
                font_small = ImageFont.truetype(fp, 12)
                break
            except:
                continue
    if font is None:
        font = ImageFont.load_default()

    for idx, (img_path, label) in enumerate(zip(selected_images, labels_for_display)):
        row, col = idx // 3, idx % 3
        x = gap + col * (cell_w + gap)
        y = gap + row * (cell_h + label_h + gap)

        # 载入并缩放图片
        try:
            img = Image.open(img_path).convert('RGB')
            # 保持宽高比缩放
            img_ratio = img.width / img.height
            cell_ratio = cell_w / cell_h
            if img_ratio > cell_ratio:
                new_w = cell_w
                new_h = int(cell_w / img_ratio)
            else:
                new_h = cell_h
                new_w = int(cell_h * img_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)

            # 居中粘贴
            paste_x = x + (cell_w - new_w) // 2
            paste_y = y + (cell_h - new_h) // 2
            canvas.paste(img, (paste_x, paste_y))

            # 边框
            draw.rectangle([x, y, x+cell_w, y+cell_h], outline='#CCCCCC', width=1)
        except Exception as e:
            draw.rectangle([x, y, x+cell_w, y+cell_h], fill='#F8F8F8', outline='#CCCCCC')
            draw.text((x+cell_w//2, y+cell_h//2), '加载失败', fill='#999', anchor='mm', font=font)

        # 标签
        label_y = y + cell_h + 4
        for li, line in enumerate(label.split('\n')):
            draw.text((x + cell_w//2, label_y + li*16), line.strip(), fill='#555',
                      anchor='ma', font=font_small if li > 0 else font)

    # 标题
    title_y = gap // 2
    draw.text((grid_w//2, 2), 'CCPD2019 数据集 — 7 个子集样本展示', fill='#2C3E50',
              anchor='ma', font=font)

    output_path = os.path.join(OUTPUT, '04_CCPD样本网格.png')
    canvas.save(output_path, quality=95)
    print(f"  ✅ 04_CCPD样本网格.png 已生成 ({len(selected_images)} 张样本)")


# ============================================================
# 素材-12: 模型性能对比柱状图
# ============================================================
def generate_comparison_chart():
    print("生成 素材-12: 模型性能对比柱状图...")

    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti SC', 'PingFang SC', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # === 左图: mAP 对比 ===
    models = ['YOLOv11n\n(2.6M 参数)', 'YOLOv8m ⭐\n(25.9M 参数)']
    map50 = [0.15, 0.995]
    map50_95 = [0.10, 0.981]

    x = np.arange(len(models))
    width = 0.3

    bars1 = ax1.bar(x - width/2, map50, width, label='mAP50', color='#3498DB', edgecolor='white', linewidth=0.5)
    bars2 = ax1.bar(x + width/2, map50_95, width, label='mAP50-95', color='#2ECC71', edgecolor='white', linewidth=0.5)

    # 添加数值标签
    for bar in bars1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h + 0.02, f'{h:.3f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold', color='#2980B9')
    for bar in bars2:
        h = bar.get_height()
        color = '#27AE60' if h > 0.5 else '#E74C3C'
        ax1.text(bar.get_x() + bar.get_width()/2., h + 0.02, f'{h:.3f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold', color=color)

    # 标注提升倍数
    ax1.annotate('', xy=(1 + width/2, 0.981), xytext=(0 + width/2, 0.10),
                arrowprops=dict(arrowstyle='<->', color='#E74C3C', lw=2))
    ax1.text(0.5, 0.55, '↑ ~10×', ha='center', fontsize=13, fontweight='bold', color='#E74C3C',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FDEDEC', edgecolor='#E74C3C', alpha=0.9))

    ax1.set_xticks(x)
    ax1.set_xticklabels(models, fontsize=11)
    ax1.set_ylabel('mAP Score', fontsize=12, fontweight='bold')
    ax1.set_title('车牌检测精度对比 (CCPD2019)', fontsize=14, fontweight='bold', color='#2C3E50')
    ax1.legend(loc='upper left', fontsize=10)
    ax1.set_ylim(0, 1.15)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # === 右图: 训练效率对比 ===
    metrics = ['训练轮次\n(成功次数)', '训练耗时\n(小时)', '模型大小\n(10MB)']
    yolo11n_vals = [6, 9, 0.5]   # 6次尝试, ~9h累计, 5MB
    yolov8m_vals = [1, 2.5, 5.0]  # 1次成功, 2.5h, 50MB

    y = np.arange(len(metrics))
    height = 0.3

    ax2.barh(y - height/2, yolo11n_vals, height, label='YOLOv11n (失败)', color='#E74C3C', alpha=0.85)
    ax2.barh(y + height/2, yolov8m_vals, height, label='YOLOv8m ⭐ (成功)', color='#2ECC71', alpha=0.85)

    # 数值标签
    for i, (v11, v8) in enumerate(zip(yolo11n_vals, yolov8m_vals)):
        ax2.text(v11 + 0.1, i - height/2, str(v11), va='center', fontsize=10, color='#C0392B', fontweight='bold')
        ax2.text(v8 + 0.1, i + height/2, str(v8), va='center', fontsize=10, color='#27AE60', fontweight='bold')

    ax2.set_yticks(y)
    ax2.set_yticklabels(metrics, fontsize=11)
    ax2.set_xlabel('数值', fontsize=12, fontweight='bold')
    ax2.set_title('训练效率对比', fontsize=14, fontweight='bold', color='#2C3E50')
    ax2.legend(loc='lower right', fontsize=10)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout(pad=2)
    plt.savefig(os.path.join(OUTPUT, '12_性能对比柱状图.png'), dpi=200, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("  ✅ 12_性能对比柱状图.png 已生成")


# ============================================================
# 素材-06: 复制训练曲线
# ============================================================
def copy_training_curve():
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'runs', 'detect', 'train-9', 'results.png')
    dst = os.path.join(OUTPUT, '06_results.png')
    if os.path.exists(src):
        import shutil
        shutil.copy2(src, dst)
        print(f"  ✅ 06_results.png 已从 train-9 复制")
    else:
        print(f"  ⚠️ train-9/results.png 未找到: {src}")

def copy_val_batch():
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'runs', 'detect', 'train-9', 'val_batch0_pred.jpg')
    dst = os.path.join(OUTPUT, '07_val_batch.jpg')
    if os.path.exists(src):
        import shutil
        shutil.copy2(src, dst)
        print(f"  ✅ 07_val_batch.jpg 已从 train-9 复制")
    else:
        print(f"  ⚠️ train-9/val_batch0_pred.jpg 未找到: {src}")


if __name__ == '__main__':
    print("=" * 50)
    print("生成实验报告素材")
    print("=" * 50)
    generate_timeline()
    generate_ccpd_grid()
    generate_comparison_chart()
    copy_training_curve()
    copy_val_batch()
    print("\n✅ 所有素材已生成到 docs/materials/")
