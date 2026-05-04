# mqtt_integration.py
"""
MQTT integration for DMS - bridges between modules and MQTT broker
"""
import threading
import time
from typing import Dict, Any, Optional

from mqtt_manager import MQTTManager

# Global MQTT instance
_mqtt_manager: Optional[MQTTManager] = None
_mqtt_enabled = False
_mqtt_lock = threading.Lock()

# Publish throttling
_last_publish = {"vision": 0, "telemetry": 0}
PUBLISH_INTERVALS = {
    "vision": 0.2,      # 5 Hz
    "face": 0.5,        # 2 Hz  
    "telemetry": 30.0,  # 30 seconds
    "status": 60.0,     # 60 seconds
}


def init_mqtt(broker_host: str = "localhost",
              broker_port: int = 1883,
              username: str = None,
              password: str = None) -> bool:
    """Initialize MQTT connection"""
    global _mqtt_manager, _mqtt_enabled
    
    try:
        _mqtt_manager = MQTTManager(
            broker_host=broker_host,
            broker_port=broker_port,
            username=username,
            password=password
        )
        
        # Register command handlers
        _mqtt_manager.register_command("snapshot", _handle_snapshot_command)
        _mqtt_manager.register_command("reset_alerts", _handle_reset_alerts_command)
        _mqtt_manager.register_command("set_threshold", _handle_set_threshold_command)
        _mqtt_manager.register_command("reboot", _handle_reboot_command)
        
        if _mqtt_manager.connect():
            _mqtt_enabled = True
            print(f"[MQTT] Enabled - connected to {broker_host}:{broker_port}")
            return True
        else:
            print(f"[MQTT] Failed to connect to {broker_host}:{broker_port}")
            return False
            
    except Exception as e:
        print(f"[MQTT] Init failed: {e}")
        _mqtt_enabled = False
        return False


def is_mqtt_enabled() -> bool:
    return _mqtt_enabled and _mqtt_manager and _mqtt_manager.connected


def shutdown_mqtt():
    """Shutdown MQTT connection"""
    global _mqtt_enabled
    if _mqtt_manager:
        _mqtt_manager.disconnect()
    _mqtt_enabled = False
    print("[MQTT] Shutdown complete")


# ==================== Command Handlers ====================

_snapshot_callback = None
_reset_alerts_callback = None
_threshold_callback = None
_reboot_callback = None


def set_callbacks(snapshot_cb=None, reset_alerts_cb=None, 
                  threshold_cb=None, reboot_cb=None):
    """Set callbacks for remote commands"""
    global _snapshot_callback, _reset_alerts_callback, _threshold_callback, _reboot_callback
    _snapshot_callback = snapshot_cb
    _reset_alerts_callback = reset_alerts_cb
    _threshold_callback = threshold_cb
    _reboot_callback = reboot_cb


def _handle_snapshot_command(payload: Dict):
    """Handle remote snapshot request"""
    print(f"[MQTT] Received snapshot command")
    if _snapshot_callback:
        _snapshot_callback(payload)
        _mqtt_manager.publish_command_response("snapshot", True)
    else:
        _mqtt_manager.publish_command_response("snapshot", False, "No handler")


def _handle_reset_alerts_command(payload: Dict):
    """Handle reset alerts command"""
    print(f"[MQTT] Received reset_alerts command")
    if _reset_alerts_callback:
        _reset_alerts_callback(payload)
        _mqtt_manager.publish_command_response("reset_alerts", True)
    else:
        _mqtt_manager.publish_command_response("reset_alerts", False, "No handler")


def _handle_set_threshold_command(payload: Dict):
    """Handle set threshold command"""
    threshold = payload.get("threshold")
    task = payload.get("task", "drowsiness")
    print(f"[MQTT] Received set_threshold: {task}={threshold}")
    if _threshold_callback:
        _threshold_callback(task, threshold)
        _mqtt_manager.publish_command_response("set_threshold", True)
    else:
        _mqtt_manager.publish_command_response("set_threshold", False, "No handler")


def _handle_reboot_command(payload: Dict):
    """Handle reboot command"""
    print(f"[MQTT] Received reboot command")
    if _reboot_callback:
        _reboot_callback(payload)
        _mqtt_manager.publish_command_response("reboot", True)
    else:
        _mqtt_manager.publish_command_response("reboot", False, "No handler")


# ==================== Publishing Functions ====================

def publish_vision(predictions: Dict, fps: float):
    """Publish vision predictions with throttling"""
    if not is_mqtt_enabled():
        return
        
    now = time.time()
    if now - _last_publish.get("vision", 0) >= PUBLISH_INTERVALS["vision"]:
        _last_publish["vision"] = now
        _mqtt_manager.publish_vision(predictions, fps)


def publish_audio(audio_result: Dict):
    """Publish audio results"""
    if not is_mqtt_enabled():
        return
    _mqtt_manager.publish_audio(audio_result)


def publish_alert(alert_type: str, severity: str, details: Dict):
    """Publish immediate alert"""
    if not is_mqtt_enabled():
        return
    _mqtt_manager.publish_alert(alert_type, severity, details)


def publish_face(face_state: Dict):
    """Publish face verification with throttling"""
    if not is_mqtt_enabled():
        return
        
    now = time.time()
    if now - _last_publish.get("face", 0) >= PUBLISH_INTERVALS["face"]:
        _last_publish["face"] = now
        _mqtt_manager.publish_face(face_state)


def publish_telemetry(camera_ok: bool, audio_ok: bool, fps: float, uptime: float):
    """Publish system telemetry"""
    if not is_mqtt_enabled():
        return
        
    now = time.time()
    if now - _last_publish.get("telemetry", 0) >= PUBLISH_INTERVALS["telemetry"]:
        _last_publish["telemetry"] = now
        _mqtt_manager.publish_telemetry({
            "camera_ok": camera_ok,
            "audio_ok": audio_ok,
            "fps": fps,
            "uptime_seconds": uptime,
        })