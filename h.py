import cv2
import os

cap = cv2.VideoCapture("p2/test_video.mp4")  # update path to your real video filename
fps = cap.get(cv2.CAP_PROP_FPS)

os.makedirs("debug_frames", exist_ok=True)
target_times = [5.5, 5.6, 5.7, 5.76, 5.8, 5.9, 6.0]
for t in target_times:
    frame_num = int(t * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f"debug_frames/frame_{t}.jpg", frame)
        print(f"saved frame at t={t}s (frame {frame_num})")
cap.release()