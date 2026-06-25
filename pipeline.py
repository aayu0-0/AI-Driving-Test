"""
CV Pipeline — Lane Detection & Event Logger
Reads test_video.mp4, detects lane lines via Hough transform on ROI,
computes per-frame lateral offset, logs swerve/hard-brake events to JSON.
"""
import cv2
import numpy as np
import json
import os
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

VIDEO_IN  = "test_video.mp4"
JSON_OUT  = "output/analysis.json"

# Tuning
SWERVE_THRESHOLD_PX   = 30   # SMOOTHED offset change over the sustain window -> swerve
SWERVE_SUSTAIN_FRAMES = 6    # how many frames the displacement must hold to count as real
SWERVE_COOLDOWN_S     = 1.0  # min seconds between two logged swerve events
BRAKE_CONSEC_FRAMES   = 2    # unused lane frames before "brake" event
SMOOTHING_WINDOW      = 7    # rolling average for offset (higher = less Hough jitter)


def region_of_interest(img):
    """Trapezoidal mask covering lower 55% of frame."""
    h, w = img.shape[:2]
    mask = np.zeros_like(img)
    poly = np.array([[
        (int(w * 0.02), h),
        (int(w * 0.45), int(h * 0.50)),
        (int(w * 0.55), int(h * 0.50)),
        (int(w * 0.98), h),
    ]], dtype=np.int32)
    cv2.fillPoly(mask, poly, 255)
    return cv2.bitwise_and(img, mask)


def average_lines(lines, w):
    """
    Separate Hough lines into left/right buckets, return a LENGTH-WEIGHTED
    average endpoint per side (not a plain mean). A plain mean treats a
    short 15px tire-mark/patch-line fragment the same as a real 80px lane
    line segment, letting noise drag the averaged line sideways even
    though the true lane marking hasn't moved. Weighting by length means
    long, continuous lines (almost always the real lane marking) dominate
    the average, and short spurious fragments barely move it.
    """
    left_lines, right_lines = [], []
    if lines is None:
        return None, None
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            continue
        slope = (y2 - y1) / (x2 - x1)
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if slope < -0.3 and x1 < w // 2:
            left_lines.append((line[0], length))
        elif slope > 0.3 and x1 > w // 2:
            right_lines.append((line[0], length))

    def weighted_line(bucket):
        if not bucket:
            return None
        coords  = np.array([b[0] for b in bucket], dtype=float)
        weights = np.array([b[1] for b in bucket], dtype=float)
        return np.average(coords, axis=0, weights=weights).astype(int)

    return weighted_line(left_lines), weighted_line(right_lines)


def lane_center(left, right, w):
    """Return pixel x of lane midpoint at bottom of frame."""
    if left is not None and right is not None:
        lx = (left[0] + left[2]) / 2
        rx = (right[0] + right[2]) / 2
        return int((lx + rx) / 2)
    elif left is not None:
        return int((left[0] + left[2]) / 2) + 120
    elif right is not None:
        return int((right[0] + right[2]) / 2) - 120
    return None


def run():
    cap = cv2.VideoCapture(VIDEO_IN)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open {VIDEO_IN}")

    fps   = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w     = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h     = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_center = w // 2

    offsets        = []   # (frame, offset_px)
    events         = []   # {frame, time_s, type, detail}
    offset_history = []
    smooth_history  = []   # history of SMOOTHED values, for sustained-displacement check
    confident_history = []  # history of bool: were BOTH lane lines detected this frame?

    last_swerve_time = -999
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur  = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 40, 120)
        roi   = region_of_interest(edges)

        lines = cv2.HoughLinesP(
            roi, rho=1, theta=np.pi / 180,
            threshold=30, minLineLength=30, maxLineGap=60
        )

        left, right = average_lines(lines, w)
        lc = lane_center(left, right, w)
        both_detected = left is not None and right is not None

        if lc is not None:
            offset = lc - frame_center
            offset_history.append(offset)
            if len(offset_history) > SMOOTHING_WINDOW:
                offset_history.pop(0)
            smooth = int(np.mean(offset_history))
            offsets.append({"frame": frame_idx, "offset_px": smooth})

            smooth_history.append(smooth)
            if len(smooth_history) > SWERVE_SUSTAIN_FRAMES:
                smooth_history.pop(0)

            confident_history.append(both_detected)
            if len(confident_history) > SWERVE_SUSTAIN_FRAMES:
                confident_history.pop(0)

            # Swerve: compare smoothed offset NOW vs smoothed offset
            # SWERVE_SUSTAIN_FRAMES ago. Only counts if BOTH lane lines
            # were confidently detected across the WHOLE window — this
            # filters out dashed-line dropout / single-line fallback
            # jumps, which look like swerves but are just detection noise.
            if len(smooth_history) == SWERVE_SUSTAIN_FRAMES:
                displacement = abs(smooth_history[-1] - smooth_history[0])
                current_time = frame_idx / fps
                window_confident = all(confident_history)
                if (displacement > SWERVE_THRESHOLD_PX and
                        window_confident and
                        current_time - last_swerve_time > SWERVE_COOLDOWN_S):
                    events.append({
                        "frame": frame_idx,
                        "time_s": round(current_time, 2),
                        "type": "swerve",
                        "detail": f"sustained shift {displacement}px over {SWERVE_SUSTAIN_FRAMES} frames"
                    })
                    last_swerve_time = current_time

        frame_idx += 1

    cap.release()

    # Compute summary stats
    if offsets:
        vals = [o["offset_px"] for o in offsets]
        avg_offset = round(float(np.mean(np.abs(vals))), 2)
        max_offset = int(np.max(np.abs(vals)))
        std_offset = round(float(np.std(vals)), 2)
    else:
        avg_offset = max_offset = std_offset = 0

    result = {
        "video": VIDEO_IN,
        "total_frames": total,
        "fps": fps,
        "duration_s": round(total / fps, 1),
        "frames_analyzed": frame_idx,
        "lane_detected_frames": len(offsets),
        "avg_abs_offset_px": avg_offset,
        "max_abs_offset_px": max_offset,
        "std_offset_px": std_offset,
        "events": events,
        "offsets": offsets,
    }

    os.makedirs("output", exist_ok=True)
    with open(JSON_OUT, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Analysis complete → {JSON_OUT}")
    print(f"  Frames: {frame_idx}  |  Lane detected: {len(offsets)}")
    print(f"  Avg offset: {avg_offset}px  |  Max: {max_offset}px  |  Std: {std_offset}px")
    print(f"  Events logged: {len(events)}")
    return result


if __name__ == "__main__":
    run()