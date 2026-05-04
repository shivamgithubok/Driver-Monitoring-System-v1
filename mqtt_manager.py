# mqtt_manager.py
import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MQTTManager:
    """MQTT client for DMS edge device"""
    
    def __init__(self, broker_host: str = "localhost", 
                 broker_port: int = 1883,
                 client_id: Optional[str] = None,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 use_tls: bool = False):
        
        import socket
        if client_id is None:
            client_id = f"dms_edge_{socket.gethostname()}"
        
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.username = username
        self.password = password
        self.use_tls = use_tls
        
        self.client = None
        self.connected = False
        self._running = False
        self._thread = None
        
        # Topic structure
        self.device_id = client_id
        self.topics = {
            "base": f"dms/{self.device_id}",
            "vision": f"dms/{self.device_id}/vision",
            "audio": f"dms/{self.device_id}/audio",
            "alert": f"dms/{self.device_id}/alert",
            "face": f"dms/{self.device_id}/face",
            "status": f"dms/{self.device_id}/status",
            "telemetry": f"dms/{self.device_id}/telemetry",
            "command": f"dms/{self.device_id}/command",
            "command_response": f"dms/{self.device_id}/command/response",
        }
        
        self._command_callbacks: Dict[str, Callable] = {}
        self._setup_client()
        
    def _setup_client(self):
        """Initialize MQTT client with callbacks"""
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, 
                                   client_id=self.client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Authentication
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        # TLS
        if self.use_tls:
            self.client.tls_set()
            
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when connected to broker"""
        if rc == 0:
            self.connected = True
            logger.info(f"MQTT connected to {self.broker_host}:{self.broker_port}")
            
            # Subscribe to command topics
            self.client.subscribe(self.topics["command"])
            logger.info(f"Subscribed to {self.topics['command']}")
            
            # Publish online status
            self._publish_status("online")
        else:
            logger.error(f"MQTT connection failed (code: {rc})")
            self.connected = False
            
    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback when disconnected"""
        logger.warning("MQTT disconnected")
        self.connected = False
        
    def _on_message(self, client, userdata, msg):
        """Handle incoming messages"""
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get("command")
            
            if command and command in self._command_callbacks:
                self._command_callbacks[command](payload)
            else:
                logger.debug(f"Unknown command: {command}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MQTT message: {e}")
        except Exception as e:
            logger.error(f"MQTT message handler error: {e}")
            
    def _publish_status(self, status: str):
        """Publish device status"""
        payload = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "client_id": self.client_id,
        }
        self._publish(self.topics["status"], payload, retain=True)
        
    def _publish(self, topic: str, payload: Dict[str, Any], 
                 qos: int = 0, retain: bool = False):
        """Internal publish method"""
        if not self.connected:
            logger.debug(f"Not connected, skipping publish to {topic}")
            return
            
        try:
            self.client.publish(topic, json.dumps(payload), qos=qos, retain=retain)
            logger.debug(f"Published to {topic}")
        except Exception as e:
            logger.error(f"Publish failed: {e}")
            
    def connect(self) -> bool:
        """Connect to broker and start loop"""
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            self._running = True
            return True
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from broker"""
        if self.connected:
            self._publish_status("offline")
        self._running = False
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
        
    def register_command(self, command: str, callback: Callable):
        """Register callback for a specific command"""
        self._command_callbacks[command] = callback
        
    # ==================== Publishing Methods ====================
    
    def publish_vision(self, predictions: Dict, fps: float):
        """Publish vision predictions"""
        # Extract active alerts
        alerts = []
        for task, data in predictions.items():
            if data.get("confidence", 0) > 0.6:
                alerts.append({
                    "task": task,
                    "label": data.get("label"),
                    "confidence": data.get("confidence")
                })
                
        payload = {
            "timestamp": datetime.now().isoformat(),
            "fps": round(fps, 1),
            "predictions": {
                task: {
                    "label": data.get("label"),
                    "confidence": data.get("confidence")
                }
                for task, data in predictions.items()
            },
            "alerts": alerts
        }
        self._publish(self.topics["vision"], payload, qos=1)
        
    def publish_audio(self, audio_result: Dict):
        """Publish audio analysis results"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "active": audio_result.get("active", False),
            "level": audio_result.get("level", "NONE"),
            "speaker": audio_result.get("speaker"),
            "keyword": audio_result.get("keyword"),
            "transcript": audio_result.get("transcript"),
            "fusion_score": audio_result.get("fusion_score", 0),
        }
        self._publish(self.topics["audio"], payload, qos=1)
        
    def publish_alert(self, alert_type: str, severity: str, details: Dict):
        """Publish immediate alert"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": alert_type,
            "severity": severity,
            "details": details
        }
        self._publish(self.topics["alert"], payload, qos=2)  # QOS 2 for critical
        
    def publish_face(self, face_state: Dict):
        """Publish face verification results"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "active": face_state.get("active", False),
            "match": face_state.get("match", False),
            "similarity": face_state.get("similarity", 0),
            "driver_name": face_state.get("driver_name"),
            "liveness_label": face_state.get("liveness_label", "—")
        }
        self._publish(self.topics["face"], payload, qos=1)
        
    def publish_telemetry(self, data: Dict):
        """Publish system telemetry"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            **data
        }
        self._publish(self.topics["telemetry"], payload)
        
    def publish_command_response(self, command: str, success: bool, message: str = ""):
        """Publish response to a command"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "success": success,
            "message": message
        }
        self._publish(self.topics["command_response"], payload)