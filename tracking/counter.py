"""
tracking/counter.py
越线判断 + 双向车流量统计。
"""
import supervision as sv


class LineCounter:
    def __init__(self, line_y: int = 360, min_cross_dist: float = 20):
        """
        Args:
            line_y: 横截线 y 坐标（像素）。
            min_cross_dist: 最小位移阈值（像素）。
                相邻两帧中心点位移 < 该值时跳过，用于过滤
                静止车辆的 bbox 抖动，避免产生假越线。
        """
        self.line_y = line_y
        self.min_cross_dist = min_cross_dist
        self.forward_count = 0
        self.backward_count = 0
        self.prev_positions: dict[int, float] = {}
        self.counted: dict[int, str] = {}

    def update(self, detections: sv.Detections) -> list[tuple[int, str]]:
        crossed = []

        for i, track_id in enumerate(detections.tracker_id):
            tid = int(track_id)

            y1 = detections.xyxy[i][1]
            y2 = detections.xyxy[i][3]
            center_y = (y1 + y2) / 2.0

            if tid in self.prev_positions:
                prev_y = self.prev_positions[tid]

                # 过滤 bbox 抖动：位移太小不判定越线
                if abs(center_y - prev_y) < self.min_cross_dist:
                    continue

                if prev_y < self.line_y <= center_y and tid not in self.counted:
                    self.forward_count += 1
                    self.counted[tid] = "forward"
                    crossed.append((tid, "forward"))

                elif prev_y > self.line_y >= center_y and tid not in self.counted:
                    self.backward_count += 1
                    self.counted[tid] = "backward"
                    crossed.append((tid, "backward"))

            self.prev_positions[tid] = center_y

        return crossed

    def get_direction(self, track_id: int) -> str:
        return self.counted.get(track_id, "")

    @property
    def total_count(self) -> int:
        return self.forward_count + self.backward_count
