import json
import time
import threading
import numpy as np
from collections import deque
from flask import Flask, Response, render_template, jsonify, request
import os
import time
import atexit
import sqlite3
from mqtt_integration import (
    init_mqtt, shutdown_mqtt, is_mqtt_enabled,
    publish_vision, publish_audio, publish_alert, 
    publish_face, publish_telemetry, set_callbacks
)

from dotenv import load_dotenv
load_dotenv()

from utils import get_logger
logger = get_logger("app")

import vision

try:
    from dms_pipeline import (
        DMSPipeline, VehicleContext, AlertLevel, PipelineResult,
    )
    AUDIO_AVAILABLE = True
except ImportError as e:
    AUDIO_AVAILABLE = False
    logger.warning(f"dms_pipeline not found ({e}). Audio disabled.")

try:
    from face_verification import (
        load_recognition_model as load_face_model,
        get_largest_face, passive_liveness_check,
        save_embedding, load_embedding, compare_embeddings,
        save_preview, DB_DIR, PREVIEW_DIR,
    )
    FACE_AVAILABLE = True
except ImportError as e:
    FACE_AVAILABLE = False
    logger.warning(f"face_verification not found ({e}). Face ID disabled.")

app = Flask(__name__)

audio_lock          = threading.Lock()
latest_audio_result = {
    "active":         False,
    "level":          "NONE",
    "fusion_score":   0.0,
    "yamnet_label":   "—",
    "yamnet_score":   0.0,
    "keyword":        None,
    "keyword_score":  0.0,
    "text_risk":      0.0,
    "transcript":     None,
    "speaker":        None,
    "speaker_score":  0.0,
    "latency_ms":     0.0,
    "bert_label":     "NEUTRAL",
    "bert_score":     0.0,
}
audio_event_queue = deque(maxlen=50)
audio_pipeline    = None
audio_ok          = False

DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "dms_data.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    severity TEXT,
                    message TEXT,
                    driver_name TEXT,
                    type TEXT
                 )''')
    conn.commit()
    conn.close()

init_db()

def insert_alert(severity, message, driver_name, alert_type):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO alerts (timestamp, severity, message, driver_name, type) VALUES (?, ?, ?, ?, ?)',
                  (time.time(), severity, message, driver_name, alert_type))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"DB Error: {e}")

# Enrollment progress state
enrol_state = {
    "phase":    "idle",
    "progress": 0,
    "message":  "",
    "driver_name": None,
}

face_lock       = threading.Lock()
face_app_model  = None

face_enrol_state = {
    "phase":       "idle",
    "progress":    0,
    "message":     "",
    "driver_name": None,
}

face_verify_state = {
    "active":          False,
    "match":           False,
    "similarity":      0.0,
    "liveness_label":  "—",
    "liveness_score":  0.0,
    "driver_name":     None,
}
face_verify_running = False
_start_time = None

def get_uptime():
    return time.time() - _start_time if _start_time else 0


def _on_audio_result(result: "PipelineResult"):
    with audio_lock:
        latest_audio_result.update({
            "active":        result.alert_level != AlertLevel.NONE,
            "level":         result.alert_level.name,
            "fusion_score":  round(result.fusion_score, 3),
            "yamnet_label":  result.yamnet_label,
            "yamnet_score":  round(result.yamnet_score, 3),
            "keyword":       result.keyword_hit,
            "keyword_score": round(getattr(result, "keyword_score", 0.0), 3),
            "text_risk":     round(result.text_risk, 3),
            "transcript":    result.transcript,
            "speaker":       result.speaker_id,
            "speaker_score": round(getattr(result, "speaker_score", 0.0), 3),
            "latency_ms":    round(result.latency_ms, 1),
            "bert_label":    getattr(result, "bert_label", "NEUTRAL"),
            "bert_score":    round(getattr(result, "bert_score", 0.0), 3),
        })
        
        if result.alert_level != AlertLevel.NONE:
            audio_event_queue.append({
                "ts":      time.strftime("%H:%M:%S"),
                "level":   result.alert_level.name,
                "score":   round(result.fusion_score, 3),
                "label":   result.yamnet_label,
                "kw":      result.keyword_hit,
                "text":    result.transcript,
                "speaker": result.speaker_id,
            })
            
            # NEW: Publish critical alerts to MQTT
            if is_mqtt_enabled():
                if result.alert_level in [AlertLevel.ALERT, AlertLevel.CRITICAL]:
                    publish_alert(
                        alert_type="audio",
                        severity=result.alert_level.name,
                        details={
                            "label": result.yamnet_label,
                            "keyword": result.keyword_hit,
                            "transcript": result.transcript,
                            "speaker": result.speaker_id,
                            "score": round(result.fusion_score, 3)
                        }
                    )
                # Always publish audio state
                publish_audio(latest_audio_result)

            # Update database
            insert_alert(result.alert_level.name, f"Audio: {result.yamnet_label}", result.speaker_id or "Unknown", "Audio")

def alert_monitor_worker():
    """Background thread to monitor vision predictions and track alerts/summaries."""
    prev_drowsy = False
    prev_yawn = False
    prev_dist = False
    
    while True:
        try:
            with vision.state_lock:
                preds = dict(vision.latest_predictions)
            with face_lock:
                d_name = face_verify_state.get("driver_name") or "Unknown"
            
            if preds:
                # Drowsy Check
                drow = preds.get("drowsiness", {})
                is_drow = drow.get("label") == "Drowsy" and drow.get("confidence", 0) > 0.60
                if is_drow and not prev_drowsy:
                    insert_alert("CRITICAL", "Drowsiness Detected", d_name, "Drowsy")
                prev_drowsy = is_drow

                # Yawn Check
                yawn = preds.get("yawn", {})
                is_yawn = yawn.get("label") == "Yawning" and yawn.get("confidence", 0) > 0.60
                if is_yawn and not prev_yawn:
                    insert_alert("WARNING", "Yawning Detected", d_name, "Yawn")
                prev_yawn = is_yawn

                # Distraction / Phone Check
                dist = preds.get("activity", {})
                lbl = dist.get("label", "")
                is_dist = lbl not in ["Safe Driving", "None", ""] and dist.get("confidence", 0) > 0.60
                if is_dist and not prev_dist:
                    a_type = "Phone" if ("Phone" in lbl or "phone" in lbl.lower()) else "Distraction"
                    insert_alert("WARNING", f"Distraction: {lbl}", d_name, a_type)
                prev_dist = is_dist

        except Exception as e:
            logger.error(f"[Alert Monitor] Error: {e}")
            
        time.sleep(0.5)

def mqtt_publish_worker():
    """Background thread to publish vision/telemetry to MQTT"""
    last_telemetry_time = 0
    telemetry_interval = 30  # seconds
    
    while True:
        try:
            if is_mqtt_enabled():
                # Publish vision predictions
                with vision.state_lock:
                    predictions = dict(vision.latest_predictions)
                    fps = vision.latest_fps
                if predictions:
                    publish_vision(predictions, fps)
                
                # Publish face verification
                with face_lock:
                    face_state = dict(face_verify_state)
                publish_face(face_state)
                
                # Publish telemetry periodically
                now = time.time()
                if now - last_telemetry_time >= telemetry_interval:
                    last_telemetry_time = now
                    publish_telemetry(
                        camera_ok=vision.camera_ok,
                        audio_ok=audio_ok,
                        fps=fps,
                        uptime=get_uptime()
                    )
        except Exception as e:
            logger.error(f"[MQTT Worker] Error: {e}")
            
        time.sleep(0.2)


def on_snapshot(payload):
    """Handle remote snapshot request"""
    logger.info(f"[CMD] Snapshot requested: {payload}")
    # You can save a snapshot to disk here
    try:
        with vision.state_lock:
            jpg = vision.latest_frame_jpg
        if jpg:
            snapshot_path = f"snapshot_{int(time.time())}.jpg"
            with open(snapshot_path, "wb") as f:
                f.write(jpg)
            logger.info(f"[CMD] Snapshot saved to {snapshot_path}")
        else:
            logger.warning("[CMD] Snapshot failed: No frame available")
    except Exception as e:
        logger.exception(f"Error saving snapshot: {e}")

def on_reset_alerts(payload):
    """Handle reset alerts command"""
    logger.info(f"[CMD] Reset alerts: {payload}")
    # Reset any persistent alert state
    with audio_lock:
        # Reset audio alert tracking if needed
        pass

def on_set_threshold(task, threshold):
    """Handle threshold update command"""
    logger.info(f"[CMD] Set threshold: {task} = {threshold}")
    try:
        # Update threshold in TASK_META if needed
        if task in vision.TASK_META:
            vision.TASK_META[task]["alert_threshold"] = float(threshold)
            logger.info(f"Threshold updated for {task} to {threshold}")
        else:
            logger.warning(f"Unknown task for threshold update: {task}")
    except ValueError as e:
        logger.error(f"Invalid threshold value '{threshold}' for task {task}: {e}")
    except Exception as e:
        logger.exception(f"Error setting threshold: {e}")

def on_reboot(payload):
    """Handle reboot command"""
    logger.info("[CMD] Rebooting...")
    import sys
    sys.exit(0)

    
def start_audio_pipeline():
    global audio_pipeline, audio_ok
    if not AUDIO_AVAILABLE: return
    try:
        from dms_pipeline import AlertOutput
        original_dispatch = AlertOutput.dispatch
        def patched_dispatch(self, result):
            original_dispatch(self, result)
            _on_audio_result(result)
        AlertOutput.dispatch = patched_dispatch
        audio_pipeline = DMSPipeline(mic_device=None)
        audio_pipeline.start()
        audio_ok = True
        logger.info("Audio pipeline started")
        spk = audio_pipeline.get_speaker_status()
        if spk.get("enrolled"):
            logger.info(f"Driver voiceprint loaded")
    except Exception as e:
        logger.warning(f"Audio pipeline failed: {e}")
        audio_ok = False

def _get_face_model():
    global face_app_model
    if face_app_model is None:
        if not FACE_AVAILABLE:
            raise RuntimeError("face_verification module not available")
        face_app_model = load_face_model(cpu=True)
    return face_app_model

@app.route("/")
def index():
    return render_template("index.html",
                           task_meta=json.dumps(vision.TASK_META),
                           task_order=json.dumps(vision.TASK_ORDER))

@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            with vision.state_lock:
                jpg = vision.latest_frame_jpg
            if jpg:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
            time.sleep(1 / vision.STREAM_FPS)
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/predictions")
def predictions():
    def event_stream():
        last_sent = None
        while True:
            with vision.state_lock:
                preds = dict(vision.latest_predictions)
                fps   = vision.latest_fps
            with audio_lock:
                audio_res = dict(latest_audio_result)

            payload = json.dumps({"predictions": preds, "fps": fps, "audio": audio_res})
            if payload != last_sent:
                last_sent = payload
                yield f"data: {payload}\n\n"
            time.sleep(1 / 15)
    return Response(event_stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

@app.route("/audio_events")
def audio_events():
    def event_stream():
        last_idx = 0
        while True:
            with audio_lock:
                events = list(audio_event_queue)
            for ev in events[last_idx:]:
                yield f"data: {json.dumps(ev)}\n\n"
            last_idx = len(events)
            time.sleep(0.25)
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/api/alerts")
def api_alerts():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT timestamp, severity, message, driver_name, type FROM alerts ORDER BY timestamp DESC LIMIT 100')
        rows = c.fetchall()
        conn.close()
        return jsonify([{"timestamp": r[0], "severity": r[1], "message": r[2], "driver_name": r[3], "type": r[4]} for r in rows])
    except Exception as e:
        logger.error(f"DB Fetch Error: {e}")
        return jsonify([])

@app.route("/api/activity_summary")
def api_activity_summary():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Today's midnight
        import datetime
        today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min).timestamp()
        c.execute('SELECT type, COUNT(*) FROM alerts WHERE timestamp >= ? GROUP BY type', (today_start,))
        rows = c.fetchall()
        conn.close()
        
        summary = {"Drowsy": 0, "Yawn": 0, "Phone": 0, "Audio": 0}
        for t, count in rows:
            if t in summary:
                summary[t] += count
        return jsonify(summary)
    except Exception as e:
        logger.error(f"DB Fetch Error: {e}")
        return jsonify({"Drowsy": 0, "Yawn": 0, "Phone": 0, "Audio": 0})

from flask import send_file
@app.route("/api/driver_image/<name>")
def api_driver_image(name):
    if not FACE_AVAILABLE:
        return "Face module not available", 404
    path = os.path.join(PREVIEW_DIR, f"enrolled_{name}.jpg")
    if os.path.exists(path):
        return send_file(path, mimetype='image/jpeg')
    return "Not found", 404

@app.route("/status")
def status():
    with audio_lock:
        audio_res = dict(latest_audio_result)
    speaker_status = {}
    if audio_pipeline is not None:
        speaker_status = audio_pipeline.get_speaker_status()
    return jsonify({
        "model_loaded":     vision.session is not None,
        "camera_ok":        vision.camera_ok,
        "onnx_available":   vision.ONNX_AVAILABLE,
        "model_path":       vision.MODEL_PATH,
        "audio_ok":         audio_ok,
        "audio_available":  AUDIO_AVAILABLE,
        "audio_level":      audio_res.get("level", "NONE"),
        "speaker":          speaker_status,
    })

@app.route("/audio_enrol", methods=["POST"])
def audio_enrol():
    if not audio_ok or audio_pipeline is None:
        return jsonify({"ok": False, "msg": "Audio pipeline not running"}), 503
    data = request.get_json(silent=True) or {}
    seconds = float(data.get("seconds", 5.0))
    driver_name = data.get("driver_name", "Driver")
    def _do_enrol():
        with audio_lock:
            enrol_state.update(phase="recording", progress=0, message="Recording...", driver_name=driver_name)
        try:
            enrol_done = threading.Event()
            def _actual_enrol():
                try: 
                    audio_pipeline.enrol_driver(seconds=seconds)
                except Exception as e:
                    logger.exception(f"Error in actual voice enrollment: {e}")
                finally: 
                    enrol_done.set()
            threading.Thread(target=_actual_enrol, daemon=True).start()
            elapsed = 0.0
            while not enrol_done.is_set() and elapsed < seconds + 3:
                pct = min(int((elapsed / seconds) * 90), 90)
                with audio_lock:
                    enrol_state["progress"] = pct
                    enrol_state["message"] = f"Recording... {max(0, int(seconds-elapsed))}s"
                    if elapsed >= seconds: enrol_state["phase"] = "processing"
                time.sleep(0.3); elapsed += 0.3
            enrol_done.wait(timeout=5)
            with audio_lock: enrol_state.update(phase="done", progress=100, message="Complete ✓")
        except Exception as e:
            logger.exception(f"Error in voice enrollment process: {e}")
            with audio_lock: enrol_state.update(phase="error", message="Failed")
    threading.Thread(target=_do_enrol, daemon=True).start()
    return jsonify({"ok": True, "msg": "Enrollment started"})

@app.route("/enrol_status")
def enrol_status():
    with audio_lock: return jsonify(dict(enrol_state))

@app.route("/voice_results")
def voice_results():
    with audio_lock: return jsonify(dict(latest_audio_result))

@app.route("/face_enrol", methods=["POST"])
def face_enrol():
    if not FACE_AVAILABLE: return jsonify({"ok": False}), 503
    data = request.get_json(silent=True) or {}
    driver_name = data.get("driver_name", "Driver")
    def _do_face_enrol():
        with face_lock: face_enrol_state.update(phase="capturing", progress=10, driver_name=driver_name)
        try:
            fmodel = _get_face_model()
            best_face = None; best_frame = None; best_score = 0.0
            for attempt in range(15):
                time.sleep(0.3)
                with vision.face_lock: raw = vision.latest_raw_frame
                if raw is None: continue
                face = get_largest_face(fmodel, raw)
                if face is not None and face.det_score > best_score:
                    best_face = face; best_frame = raw.copy(); best_score = face.det_score
            if best_face is None:
                with face_lock: face_enrol_state.update(phase="error", message="No face detected")
                return
            liv_label, liv_score, is_real = passive_liveness_check(best_frame, best_face.bbox)
            if not is_real:
                with face_lock: face_enrol_state.update(phase="error", message="Liveness FAILED")
                return
            save_embedding(driver_name, best_face.embedding)
            import cv2 as _cv2
            preview = best_frame.copy()
            save_preview(preview, f"enrolled_{driver_name}.jpg")
            with face_lock: face_enrol_state.update(phase="done", progress=100)
        except Exception as e:
            logger.exception(f"Error in face enrollment: {e}")
            with face_lock: face_enrol_state.update(phase="error", message=str(e))
    threading.Thread(target=_do_face_enrol, daemon=True).start()
    return jsonify({"ok": True})

@app.route("/face_enrol_status")
def face_enrol_status():
    with face_lock: return jsonify(dict(face_enrol_state))

@app.route("/face_verify_start", methods=["POST"])
def face_verify_start():
    global face_verify_running
    if not FACE_AVAILABLE: return jsonify({"ok": False}), 503
    data = request.get_json(silent=True) or {}
    driver_name = data.get("driver_name") or None

    # Auto-detect enrolled driver if name not provided
    if not driver_name:
        try:
            enrolled = [f.replace(".npy", "") for f in os.listdir(DB_DIR) if f.endswith(".npy")]
            if enrolled:
                driver_name = enrolled[0]
                logger.info(f"Auto-detected enrolled driver: {driver_name}")
            else:
                return jsonify({"ok": False, "msg": "No enrolled drivers found. Please enrol first."}), 400
        except Exception as e:
            logger.error(f"Could not auto-detect driver name: {e}")
            return jsonify({"ok": False, "msg": "Could not detect enrolled driver"}), 500

    if face_verify_running: return jsonify({"ok": True})
    face_verify_running = True
    def _verify_loop():
        global face_verify_running
        try:
            fmodel = _get_face_model()
            enrolled_emb = load_embedding(driver_name)
            while face_verify_running:
                with vision.face_lock: raw = vision.latest_raw_frame
                if raw is None: time.sleep(0.3); continue
                face = get_largest_face(fmodel, raw)
                if face is None:
                    with face_lock: face_verify_state.update(active=True, match=False, liveness_label="No Face")
                    time.sleep(0.3); continue
                ll, ls, is_real = passive_liveness_check(raw, face.bbox)
                if not is_real:
                    with face_lock: face_verify_state.update(active=True, match=False, liveness_label=ll)
                else:
                    sim, is_match = compare_embeddings(face.embedding, enrolled_emb, 0.45)
                    with face_lock: face_verify_state.update(active=True, match=is_match, similarity=round(sim,3), driver_name=driver_name)
                time.sleep(0.5)
        except Exception as e:
            logger.exception(f"Error in face verification loop: {e}")
        finally:
            face_verify_running = False
            with face_lock: face_verify_state["active"] = False
    threading.Thread(target=_verify_loop, daemon=True).start()
    return jsonify({"ok": True})

@app.route("/face_verify_status")
def face_verify_status():
    with face_lock: state = dict(face_verify_state)
    state["active"] = bool(state.get("active", False))
    state["match"] = bool(state.get("match", False))
    return jsonify(state)

@app.route("/face_verify_stop", methods=["POST"])
def face_verify_stop():
    global face_verify_running
    face_verify_running = False
    return jsonify({"ok": True})

@app.route("/face_status")
def face_status_route():
    import os
    enrolled = []
    if FACE_AVAILABLE and os.path.exists(DB_DIR):
        enrolled = [f.replace(".npy","") for f in os.listdir(DB_DIR) if f.endswith(".npy")]
    return jsonify({"available": FACE_AVAILABLE, "enrolled": len(enrolled)>0, "enrolled_names": enrolled})

if __name__ == "__main__":
    _start_time = time.time()
    
    # Initialize components
    vision.load_model()
    start_audio_pipeline()
    vision.init_audio_bridge(audio_lock, latest_audio_result, audio_pipeline, audio_ok)
    
    # Start camera thread
    threading.Thread(target=vision.camera_thread, daemon=True).start()
    
    # Start alert monitor thread
    threading.Thread(target=alert_monitor_worker, daemon=True).start()
    
    # Auto-start face verification if enrolled driver exists
    try:
        if FACE_AVAILABLE and os.path.exists(DB_DIR):
            enrolled = [f.replace(".npy", "") for f in os.listdir(DB_DIR) if f.endswith(".npy")]
            if enrolled:
                driver_name = enrolled[0]
                face_verify_running = True
                def _auto_verify_loop():
                    global face_verify_running
                    try:
                        fmodel = _get_face_model()
                        enrolled_emb = load_embedding(driver_name)
                        while face_verify_running:
                            with vision.face_lock: raw = vision.latest_raw_frame
                            if raw is None: time.sleep(0.3); continue
                            face = get_largest_face(fmodel, raw)
                            if face is None:
                                with face_lock: face_verify_state.update(active=True, match=False, liveness_label="No Face")
                                time.sleep(0.3); continue
                            ll, ls, is_real = passive_liveness_check(raw, face.bbox)
                            if not is_real:
                                with face_lock: face_verify_state.update(active=True, match=False, liveness_label=ll)
                            else:
                                sim, is_match = compare_embeddings(face.embedding, enrolled_emb, 0.45)
                                with face_lock: face_verify_state.update(active=True, match=is_match, similarity=round(sim,3), driver_name=driver_name)
                            time.sleep(0.5)
                    except Exception as e:
                        logger.exception(f"Error in auto face verification loop: {e}")
                    finally:
                        face_verify_running = False
                        with face_lock: face_verify_state["active"] = False
                threading.Thread(target=_auto_verify_loop, daemon=True).start()
                logger.info(f"Auto-started face verification for driver: {driver_name}")
    except Exception as e:
        logger.error(f"Could not auto-start face verify: {e}")
    
    # Initialize MQTT from environment variables
    mqtt_host = os.environ.get("MQTT_BROKER_HOST", "localhost")
    mqtt_port = int(os.environ.get("MQTT_BROKER_PORT", 1883))
    mqtt_user = os.environ.get("MQTT_USERNAME")
    mqtt_pass = os.environ.get("MQTT_PASSWORD")
    
    if os.environ.get("MQTT_ENABLED", "true").lower() == "true":
        set_callbacks(
            snapshot_cb=on_snapshot,
            reset_alerts_cb=on_reset_alerts,
            threshold_cb=on_set_threshold,
            reboot_cb=on_reboot
        )
        init_mqtt(broker_host=mqtt_host, broker_port=mqtt_port,
                  username=mqtt_user, password=mqtt_pass)
        
        # Start MQTT publish worker
        mqtt_thread = threading.Thread(target=mqtt_publish_worker, daemon=True)
        mqtt_thread.start()
    
    # Register shutdown handler
    atexit.register(shutdown_mqtt)
    
    logger.info("All systems ready")
    logger.info("Open http://localhost:5000")
    
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)