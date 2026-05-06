import cv2
import time
import threading
import numpy as np
from collections import deque
from utils import get_logger

logger = get_logger("vision")

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

import mediapipe as mp

from config import (
    CAMERA_INDEX, STREAM_FPS, JPEG_QUALITY, IMG_SIZE, MEAN, STD, FACE_MARGIN,
    VISION_MODEL_PATH as MODEL_PATH,
    TASK_META, TASK_ORDER, ONNX_OUTPUT_ORDER
)

# ── MediaPipe face detection for face cropping ──
_mp_face    = mp.solutions.face_detection
_face_det   = _mp_face.FaceDetection(model_selection=0,
                                      min_detection_confidence=0.5)

state_lock         = threading.Lock()
latest_frame_jpg   = None
latest_predictions = {}
latest_fps         = 0.0
camera_ok          = False

face_lock          = threading.Lock()
latest_raw_frame   = None

# External state references (Audio)
_audio_lock = None
_latest_audio_result = None
_audio_pipeline = None
_audio_ok = False

def init_audio_bridge(lock, result, pipeline, ok_flag):
    global _audio_lock, _latest_audio_result, _audio_pipeline, _audio_ok
    _audio_lock = lock
    _latest_audio_result = result
    _audio_pipeline = pipeline
    _audio_ok = ok_flag

session = None

def load_model():
    global session
    if not ONNX_AVAILABLE:
        return
    try:
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = 4
        session = ort.InferenceSession(
            MODEL_PATH,
            sess_options=opts,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        logger.info(f"Vision model loaded: {MODEL_PATH}")
        logger.info(f"     Provider: {session.get_providers()[0]}")

        # Verify output count
        outputs = session.get_outputs()
        n_out = len(outputs)
        logger.info(f"     Outputs: {n_out}  (expected {len(ONNX_OUTPUT_ORDER)})")
        for i, out in enumerate(outputs):
            logger.info(f"       [{i}] {out.name}")

    except Exception as e:
        logger.warning(f"Vision model not loaded ({e}). Demo mode.")
        session = None

def _crop_face(frame_bgr):
    h, w = frame_bgr.shape[:2]
    rgb  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    res  = _face_det.process(rgb)

    if res.detections:
        best = max(res.detections,
                   key=lambda d: d.location_data.relative_bounding_box.width *
                                 d.location_data.relative_bounding_box.height)
        bb = best.location_data.relative_bounding_box
        mx = FACE_MARGIN * bb.width
        my = FACE_MARGIN * bb.height
        x1 = max(0, int((bb.xmin - mx) * w))
        y1 = max(0, int((bb.ymin - my) * h))
        x2 = min(w, int((bb.xmin + bb.width  + mx) * w))
        y2 = min(h, int((bb.ymin + bb.height + my) * h))
        face = frame_bgr[y1:y2, x1:x2]
        if face.size > 0:
            return cv2.resize(face, (IMG_SIZE, IMG_SIZE)), (x1, y1, x2, y2)

    return cv2.resize(frame_bgr, (IMG_SIZE, IMG_SIZE)), None

def preprocess(frame_bgr):
    face_img, bbox = _crop_face(frame_bgr)
    rgb  = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
    norm = (rgb.astype(np.float32) / 255.0 - MEAN) / STD
    return norm.transpose(2, 0, 1)[np.newaxis], bbox

def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()

_demo_t = 0.0
def demo_predictions() -> dict:
    global _demo_t
    _demo_t += 0.04
    t = _demo_t
    results = {}
    for task, meta in TASK_META.items():
        n     = len(meta["classes"])
        base  = np.array([0.5 + 0.4 * np.sin(t + i * 1.3) for i in range(n)], dtype=np.float32)
        probs = softmax(base)
        pred  = int(np.argmax(probs))
        results[task] = {
            "pred":       pred,
            "label":      meta["classes"][pred],
            "confidence": float(probs[pred]),
            "probs":      {meta["classes"][i]: float(p) for i, p in enumerate(probs)},
        }
    return results

_buffers: dict = {task: deque(maxlen=15) for task in TASK_META}
def smooth_predictions(raw: dict) -> dict:
    smoothed = {}
    for task, result in raw.items():
        probs_arr = np.array(list(result["probs"].values()), dtype=np.float32)
        _buffers[task].append(probs_arr)
        avg  = np.mean(_buffers[task], axis=0)
        pred = int(np.argmax(avg))
        meta = TASK_META[task]
        smoothed[task] = {
            "pred":       pred,
            "label":      meta["classes"][pred],
            "confidence": float(avg[pred]),
            "probs":      {meta["classes"][i]: float(p) for i, p in enumerate(avg)},
        }
    return smoothed

def _draw_overlay(frame: np.ndarray, preds: dict, face_bbox=None) -> np.ndarray:
    h, w = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    cv2.putText(frame, "DMS LIVE", (10, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 229, 160), 2)

    drow = preds.get("drowsiness", {})
    if drow.get("label") == "Drowsy" and drow.get("confidence", 0) > 0.65:
        cv2.rectangle(frame, (0, h - 56), (w, h), (0, 0, 200), -1)
        cv2.putText(frame, "DROWSINESS DETECTED",
                    (w // 2 - 145, h - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)

    eye = preds.get("eye_state", {})
    if eye.get("label") == "Closed" and eye.get("confidence", 0) > 0.80:
        cv2.putText(frame, "EYES CLOSED", (w - 200, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)

    age = preds.get("age", {})
    if age.get("label") == "Minor" and age.get("confidence", 0) > 0.55:
        cv2.rectangle(frame, (0, 52), (w, 84), (180, 0, 0), -1)
        cv2.putText(frame, "MINOR DETECTED",
                    (10, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 220, 100), 2)

    dist = preds.get("distraction", {})
    act = preds.get("activity", {})
    if dist.get("label") == "Distracted" and dist.get("confidence", 0) > 0.60:
        activity_label = act.get("label", "")
        if activity_label == "None":
            activity_label = ""
        else:
            activity_label = f" [{activity_label}]"
        y_pos = h - 70 if drow.get("label") == "Drowsy" else h - 18
        cv2.putText(frame, f"DISTRACTED{activity_label}",
                    (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 170, 0), 2)

    # Audio bridge alert
    if _audio_lock and _latest_audio_result:
        with _audio_lock:
            audio = dict(_latest_audio_result)
        if audio.get("active") and audio.get("level") in ("ALERT", "CRITICAL"):
            y_start = 84 if (age.get("label") == "Minor") else 52
            cv2.rectangle(frame, (0, y_start), (w, y_start + 34), (0, 80, 220), -1)
            spk = audio.get("speaker", "")
            kw  = audio.get("keyword", "")
            txt = f"AUDIO [{spk}]: {audio.get('yamnet_label', '')}"
            if kw: txt += f" | KW: {kw}"
            cv2.putText(frame, txt, (10, y_start + 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 200, 80), 2)

    if face_bbox:
        x1, y1, x2, y2 = face_bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 229, 160), 2)

    return frame

def _blank_frame() -> np.ndarray:
    f = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(f, "NO CAMERA", (220, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (80, 80, 80), 2)
    return f

def camera_thread():
    global latest_frame_jpg, latest_predictions, latest_fps, camera_ok, latest_raw_frame

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS,          STREAM_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

    camera_ok = cap.isOpened()
    if not camera_ok: logger.warning("Camera not found. Demo mode.")

    frame_times = deque(maxlen=30)

    while True:
        t0 = time.time()
        if camera_ok:
            ret, frame = cap.read()
            if not ret:
                camera_ok = False
                frame = _blank_frame()
        else:
            frame = _blank_frame()
            time.sleep(1 / STREAM_FPS)

        if session is not None and camera_ok:
            try:
                inp, face_bbox = preprocess(frame)
                outs = session.run(None, {"image": inp})
                raw  = {}
                for i, task in enumerate(ONNX_OUTPUT_ORDER):
                    if i >= len(outs): break
                    logits = outs[i][0]
                    probs = softmax(logits)
                    pred  = int(np.argmax(probs))
                    meta  = TASK_META[task]
                    raw[task] = {
                        "pred":       pred,
                        "label":      meta["classes"][pred],
                        "confidence": float(probs[pred]),
                        "probs":      {meta["classes"][j]: float(p)
                                       for j, p in enumerate(probs)
                                       if j in meta["classes"]},
                    }
                preds = smooth_predictions(raw)
            except Exception as e:
                logger.error(f"Vision inference: {e}")
                preds = demo_predictions()
                face_bbox = None
        else:
            preds = demo_predictions()
            face_bbox = None

        # Audio context feedback
        if _audio_pipeline is not None and _audio_ok:
            try:
                from dms_pipeline import VehicleContext
                eye_conf = preds.get("eye_state", {}).get("confidence", 1.0)
                eye_open = 1.0 - eye_conf if preds.get("eye_state", {}).get("label") == "Closed" else eye_conf
                ctx = VehicleContext(speed_kmh=60.0, eye_openness=float(eye_open), gaze_deviation=0.0)
                _audio_pipeline.update_vehicle_context(ctx)
            except: pass

        annotated = _draw_overlay(frame.copy(), preds, face_bbox)
        _, jpg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])

        frame_times.append(time.time())
        fps = (len(frame_times) - 1) / (frame_times[-1] - frame_times[0]) if len(frame_times) > 1 else 0.0

        with state_lock:
            latest_frame_jpg   = jpg.tobytes()
            latest_predictions = preds
            latest_fps         = round(fps, 1)

        with face_lock:
            latest_raw_frame = frame.copy() if camera_ok else None

        elapsed = time.time() - t0
        time.sleep(max(0, (1 / STREAM_FPS) - elapsed))
