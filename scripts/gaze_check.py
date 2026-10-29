"""Gaze and blink, frame by frame, for talking-head edits: find every frame where the speaker looks down or blinks.

Contact sheets at 1 fps miss a 0.3 s glance at the notes and a blink on the first frame; this does not. It uses the
MediaPipe Face Landmarker (blendshapes eyeLookDown*, eyeBlink*, eyeLookIn/Out*, and the head transform) and labels
each frame:
  ok · side (clear sideways look) · down (eyes down, or the head drops while the eyes are low) · blink · no_face
Runs of closed/down frames that contain a closure and last ≤ 6 frames are blinks (the eye passes through "down" while
it closes); longer runs count as down. Head pitch is relative to a 4 s moving median, so each take keeps its posture.

Calibrate to the person: heavy eyelids read as "down" around 0.2–0.35; check a strip of their face before trusting
the thresholds (--down, --head-deg). The detector also finds "faces" in some illustrations: look at what it flags on
B-roll frames before calling it an error.

Needs `mediapipe` (pip) and the Face Landmarker model file (`face_landmarker.task`, Google, Apache 2.0, about 4 MB).
This script never downloads it: ask the person, then pass its path with --model or MOTIONSMITH_FACE_MODEL.

Usage:
  python gaze_check.py take.mp4 gaze.json --model face_landmarker.task [--fps 30] [--down 0.42] [--head-deg 10]
  python gaze_check.py --relabel gaze.json [--down …]      (new thresholds on an existing scan)
The JSON has one row per frame; the summary prints the down runs and any blink in the first second.
Run with plain `python` if mediapipe lives in your user site-packages (`-I` hides it).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np


def frames(video: str, fps: int, w: int = 720, h: int = 1280):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n = w * h * 3
    try:
        while True:
            b = p.stdout.read(n)
            if len(b) < n:
                break
            yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    finally:
        p.kill()


def label(f: dict, down: float, head_deg: float) -> str:
    if not f["face"]:
        return "no_face"
    if f["closed"] >= 0.42:
        return "closed"
    if f["down"] >= down or (abs(f["dpitch"]) >= head_deg and f["down"] >= 0.25):
        return "down"
    if f["side"] >= 0.6:
        return "side"
    return "ok"


def runs(rows: list[dict], down: float, head_deg: float) -> None:
    for f in rows:
        f["label"] = label(f, down, head_deg)
    k = 0
    while k < len(rows):
        if rows[k]["label"] not in ("closed", "down"):
            k += 1; continue
        j = k
        while j < len(rows) and rows[j]["label"] in ("closed", "down"):
            j += 1
        if any(rows[q]["label"] == "closed" for q in range(k, j)):
            for q in range(k, j):
                rows[q]["label"] = "blink" if j - k <= 6 else "down"
        elif j - k <= 3 and max(rows[q]["closed"] for q in range(k, j)) >= 0.33:   # a half blink
            for q in range(k, j):
                rows[q]["label"] = "blink"
        k = j


def scan(video: str, model: str, fps: int) -> list[dict]:
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mpt
        from mediapipe.tasks.python import vision
    except ImportError:
        sys.exit("gaze_check needs mediapipe: pip install mediapipe (run with plain python, not -I, if it is a user install)")
    opts = vision.FaceLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path=str(model)),
                                        running_mode=vision.RunningMode.VIDEO, num_faces=1,
                                        output_face_blendshapes=True, output_facial_transformation_matrixes=True,
                                        min_face_detection_confidence=0.3, min_face_presence_confidence=0.3,
                                        min_tracking_confidence=0.3)
    rows = []
    with vision.FaceLandmarker.create_from_options(opts) as lm:
        for k, fr in enumerate(frames(video, fps)):
            r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(fr)), int(k * 1000 / fps))
            row = {"f": k, "t": round(k / fps, 4)}
            if not r.face_blendshapes:
                row["face"] = False; rows.append(row); continue
            bs = {c.category_name: c.score for c in r.face_blendshapes[0]}
            R = np.array(r.facial_transformation_matrixes[0])[:3, :3]
            row.update(face=True,
                       down=round((bs["eyeLookDownLeft"] + bs["eyeLookDownRight"]) / 2, 3),
                       closed=round((bs["eyeBlinkLeft"] + bs["eyeBlinkRight"]) / 2, 3),
                       side=round(max((bs["eyeLookOutLeft"] + bs["eyeLookInRight"]) / 2, (bs["eyeLookInLeft"] + bs["eyeLookOutRight"]) / 2), 3),
                       pitch=round(math.degrees(math.atan2(-R[2, 1], R[2, 2])), 1))
            rows.append(row)
    P = np.array([f.get("pitch", np.nan) for f in rows], float)
    win = 2 * fps
    for k, f in enumerate(rows):
        if f["face"]:
            f["dpitch"] = round(float(f["pitch"] - np.nanmedian(P[max(0, k - win):k + win])), 1)
    return rows


def summary(rows: list[dict], fps: int) -> dict:
    down, cur = [], None
    for f in rows:
        if f.get("label") == "down":
            cur = cur or [f["t"], f["t"]]; cur[1] = f["t"]
        elif cur:
            down.append([cur[0], round(cur[1] + 1 / fps, 3)]); cur = None
    if cur:
        down.append([cur[0], round(cur[1] + 1 / fps, 3)])
    counts = {}
    for f in rows:
        counts[f.get("label")] = counts.get(f.get("label"), 0) + 1
    return {"frames": len(rows), "labels": counts, "down_runs": down,
            "blink_first_second": [f["t"] for f in rows if f["t"] < 1.0 and f.get("label") in ("blink", "closed")]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?"); ap.add_argument("out", nargs="?")
    ap.add_argument("--relabel", metavar="JSON")
    ap.add_argument("--model", default=os.environ.get("MOTIONSMITH_FACE_MODEL"))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--down", type=float, default=0.42, help="eyeLookDown that counts as looking down")
    ap.add_argument("--head-deg", type=float, default=10.0, help="head drop (deg, vs the take's posture) that counts with low eyes")
    a = ap.parse_args(argv)
    if a.relabel:
        rows = json.loads(Path(a.relabel).read_text(encoding="utf-8"))
        out = Path(a.relabel)
    else:
        if not (a.video and a.out):
            ap.error("give a video and an output json, or --relabel json")
        if not a.model or not Path(a.model).exists():
            ap.error("--model face_landmarker.task (not found); this script never downloads it")
        rows = scan(a.video, a.model, a.fps)
        out = Path(a.out)
    runs(rows, a.down, a.head_deg)
    out.write_text(json.dumps(rows), encoding="utf-8")
    print(json.dumps(summary(rows, a.fps), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
