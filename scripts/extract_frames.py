"""
extract_frames.py
从视频中按固定间隔抽帧，用于后续标注训练数据。
"""
import cv2
import os
import argparse


def extract_frames(video_path: str, output_dir: str = "raw_images", interval: int = 10):
    """
    从视频抽帧

    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        interval: 抽帧间隔（每 N 帧抽 1 帧）
    """
    video = cv2.VideoCapture(video_path)

    if not video.isOpened():
        print(f"❌ 无法打开视频: {video_path}")
        return

    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video.get(cv2.CAP_PROP_FPS)
    print(f"视频信息: {total_frames} 帧, {fps:.1f} FPS, "
          f"预计抽取 ~{total_frames // interval} 张")

    os.makedirs(output_dir, exist_ok=True)

    count = 0
    save_id = 0

    while True:
        ret, frame = video.read()
        if not ret:
            break

        if count % interval == 0:
            out_path = os.path.join(output_dir, f"{save_id:06d}.jpg")
            cv2.imwrite(out_path, frame)
            save_id += 1

            if save_id % 100 == 0:
                print(f"  已抽取 {save_id} 张...")

        count += 1

    video.release()
    print(f"✅ 完成！共抽取 {save_id} 张图片，保存在 {output_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从视频中按间隔抽帧")
    parser.add_argument("--video", default="../traffic.mp4", help="视频文件路径")
    parser.add_argument("--output", default="raw_images", help="输出目录")
    parser.add_argument("--interval", type=int, default=10, help="抽帧间隔")
    args = parser.parse_args()

    extract_frames(args.video, args.output, args.interval)
