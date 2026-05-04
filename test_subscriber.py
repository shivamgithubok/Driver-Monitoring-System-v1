# test_mqtt.py
import paho.mqtt.client as mqtt
import json
import time

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code: {rc}")
    if rc == 0:
        client.subscribe("test/#")
        print("Subscribed to test/#")

def on_message(client, userdata, msg):
    print(f"\n📨 [{msg.topic}] {msg.payload.decode()}")

# Create and configure client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

# Connect to broker
client.connect("localhost", 1883, 60)
client.loop_start()

# Publish test messages
for i in range(5):
    test_data = {
        "timestamp": time.time(),
        "message": f"Test message {i}",
        "status": "OK"
    }
    client.publish("test/dms", json.dumps(test_data))
    print(f"📤 Published test message {i}")
    time.sleep(2)

print("\n✅ Test complete! MQTT is working.")
time.sleep(5)
client.loop_stop()
client.disconnect()