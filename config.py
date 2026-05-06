# config.py
"""
Centralized Configuration Module for Driver Monitoring System (DMS)
Contains all general settings, paths, model sizes, and mathematical thresholds.
"""
import os
import numpy as np

# ── General Camera and Stream Settings ──
CAMERA_INDEX = 0
STREAM_FPS   = 25
JPEG_QUALITY = 80

# ── Vision Model Settings ──
VISION_MODEL_PATH = "edge_driver_model_distilled.onnx"
IMG_SIZE          = 224
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
FACE_MARGIN = 0.20

# ── Face Recognition & Liveness Settings ──
FACE_DB_DIR       = "face_db"
FACE_PREVIEW_DIR  = "face_preview"
LIVENESS_THRESHOLD = 0.40
FACE_VERIFY_THRESHOLD = 0.45

# ── Audio and Speaker Settings ──
AUDIO_SR = 16000
SPEAKER_EMBED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "driver_embedding.npy")
SPEAKER_HIGH_THRESHOLD = 0.45
SPEAKER_LOW_THRESHOLD  = 0.30

# ── MQTT Settings ──
DEFAULT_MQTT_HOST = "localhost"
DEFAULT_MQTT_PORT = 1883

# ── Task Settings ──
TASK_META = {
    "drowsiness": {
        "label": "Drowsiness", "icon": "😴",
        "classes": {0: "Alert", 1: "Drowsy"},
        "alert_class": 1, "alert_threshold": 0.65,
        "color": {"Alert": "#00e5a0", "Drowsy": "#ff4444"},
    },
    "eye_state": {
        "label": "Eye State", "icon": "👀",
        "classes": {0: "Open", 1: "Closed"},
        "alert_class": 1, "alert_threshold": 0.80,
        "color": {"Open": "#00e5a0", "Closed": "#ff4444"},
    },
    "yawn": {
        "label": "Yawn Detection", "icon": "🥱",
        "classes": {0: "No Yawn", 1: "Yawning"},
        "alert_class": 1, "alert_threshold": 0.70,
        "color": {"No Yawn": "#00e5a0", "Yawning": "#ffaa00"},
    },
    "gaze": {
        "label": "Gaze Direction", "icon": "👁",
        "classes": {
            0: "Bottom-Left",  1: "Middle-Left",  2: "Top-Left",
            3: "Bottom-Right", 4: "Middle-Right", 5: "Top-Right",
            6: "Top-Center",   7: "Bottom-Center",
        },
        "alert_class": None, "color": {},
    },
    "emotion": {
        "label": "Emotion", "icon": "🎭",
        "classes": {
            0: "Angry", 1: "Disgust", 2: "Fear",
            3: "Happy", 4: "Sad",    5: "Surprise", 6: "Neutral",
        },
        "alert_class": None,
        "color": {
            "Angry": "#ff4444", "Disgust": "#cc44ff",
            "Fear":  "#ff8800", "Happy":   "#00e5a0",
            "Sad":   "#4488ff", "Surprise":"#ffdd00",
            "Neutral":"#aaaaaa",
        },
    },
    "distraction": {
        "label": "Distraction", "icon": "🚨",
        "classes": {0: "Safe", 1: "Distracted"},
        "alert_class": 1, "alert_threshold": 0.60,
        "color": {"Safe": "#00e5a0", "Distracted": "#ff4444"},
    },
    "activity": {
        "label": "Activity", "icon": "🚗",
        "classes": {
            0: "Phone Use",  1: "Drinking",
            2: "Cigarette",  3: "Seatbelt",
            4: "None",
        },
        "alert_class": None,
        "color": {
            "Phone Use":  "#ff4444",
            "Drinking":   "#ff8800",
            "Cigarette":  "#cc44ff",
            "Seatbelt":   "#00e5a0",
            "None":       "#00e5a0",
        },
    },
    "age": {
        "label": "Age Group", "icon": "🪪",
        "classes": {0: "Minor", 1: "Young Adult", 2: "Adult"},
        "alert_class": 0, "alert_threshold": 0.55,
        "color": {
            "Minor":       "#ff4444",
            "Young Adult": "#ffaa00",
            "Adult":       "#00e5a0",
        },
    },
}

TASK_ORDER = [
    "drowsiness", "eye_state", "yawn",
    "distraction", "activity",
    "gaze", "emotion", "age",
]

ONNX_OUTPUT_ORDER = [
    "drowsiness", "gaze", "yawn", "emotion",
    "eye_state", "distraction", "activity", "age",
]
