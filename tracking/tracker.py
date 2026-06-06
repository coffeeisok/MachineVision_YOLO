"""
tracking/tracker.py
ByteTrack 跟踪器封装，基于 supervision 库。
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
        # supervision >= 0.23 API
        self.tracker = sv.ByteTrack(frame_rate=frame_rate)

    def update(self, detections: sv.Detections) -> sv.Detections:
        """
        输入 YOLO 检测结果，返回带 tracker_id 的结果。

        ByteTrack 内部流程：
        1. 卡尔曼滤波预测每个 track 在当前帧的位置
        2. 高分框先做 IOU 匹配
        3. 低分框再与未匹配的 track 做二次匹配（这是 ByteTrack 的核心创新）
        """
        if len(detections) == 0:
            detections.tracker_id = np.array([], dtype=int)
            return detections

        tracked = self.tracker.update_with_detections(detections)
        return tracked
