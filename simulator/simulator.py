import random
import time
import json
import os
import signal
import paho.mqtt.client as mqtt

# Environment variables
DEVICE_ID = os.environ.get("DEVICE_ID", "device_dev_01")
DEVICE_TYPE = os.environ.get("DEVICE_TYPE", "SMART_METER")
DEVICE_PROFILE = os.environ.get("DEVICE_PROFILE", "normal")
INTERVAL_MS = int(os.environ.get("INTERVAL_MS", "1000"))
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "power_grid/measurements")

# Certificate paths
CERT_PATH = os.environ.get("CERT_PATH", "/app/certs/certificate.pem")
KEY_PATH = os.environ.get("KEY_PATH", "/app/certs/private.key")
CA_PATH = os.environ.get("CA_PATH", "/app/certs/root-CA.crt")

# Global state
MAX_RECONNECT_ATTEMPTS = 5
reconnect_attempts = 0
client = None

# Anomaly probability by device profile
ANOMALY_CHANCE = {
    "critical": 0.40,   # 40% anomaly chance - critical grid point
    "unstable": 0.20,   # 20% anomaly chance - standard meter
    "normal": 0.05      # 5%  anomaly chance - peripheral meter
}

def generate_data():
    anomaly_chance = ANOMALY_CHANCE.get(DEVICE_PROFILE, 0.05)
    is_anomaly = random.random() < anomaly_chance

    if is_anomaly:
        # Voltage outside allowed range (±10% of 230V)
        voltage = random.choice([
            round(random.uniform(180, 206), 2),  # too low
            round(random.uniform(254, 280), 2),  # too high
        ])
        # Frequency outside allowed range
        frequency = random.choice([
            round(random.uniform(48.0, 49.7), 3),  # too low
            round(random.uniform(50.3, 52.0), 3),  # too high
        ])
        # Poor power factor
        power_factor = round(random.uniform(0.5, 0.84), 2)
        # Overcurrent
        current = round(random.uniform(21, 35), 2)
    else:
        # Normal operating conditions
        voltage = round(random.uniform(220, 240), 2)
        frequency = round(random.uniform(49.9, 50.1), 3)
        power_factor = round(random.uniform(0.92, 1.0), 2)
        current = round(random.uniform(5, 20), 2)

    active_power = round(voltage * current * power_factor, 2)

    return {
        "device_id": DEVICE_ID,
        "device_type": DEVICE_TYPE,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "voltage": voltage,
        "current": current,
        "frequency": frequency,
        "power_factor": power_factor,
        "active_power": active_power
    }

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{DEVICE_ID}] Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"[{DEVICE_ID}] Connection error: {rc}")

def on_disconnect(client, userdata, rc):
    global reconnect_attempts
    if rc != 0:
        print(f"[{DEVICE_ID}] Unexpected disconnection (code {rc})")
        while reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
            reconnect_attempts += 1
            print(f"[{DEVICE_ID}] Reconnection attempt {reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS}...")
            try:
                client.reconnect()
                reconnect_attempts = 0  # reset counter on success
                print(f"[{DEVICE_ID}] Reconnected successfully")
                return
            except Exception as e:
                print(f"[{DEVICE_ID}] Reconnection failed: {e}")
                time.sleep(5)
        print(f"[{DEVICE_ID}] Max reconnection attempts reached. Exiting.")
        exit(1)

def signal_handler(sig, frame):
    global client
    print(f"[{DEVICE_ID}] Received signal {sig}. Shutting down gracefully...")
    if client:
        client.loop_stop()
        client.disconnect()
    exit(0)

def connect_with_retry(client, broker, port, max_retries=5):
    for attempt in range(max_retries):
        try:
            client.connect(broker, port, 60)
            return True
        except Exception as e:
            print(f"[{DEVICE_ID}] Connection attempt {attempt + 1}/{max_retries} failed: {e}")
            time.sleep(5)
    return False

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# MQTT client setup
client = mqtt.Client(client_id=DEVICE_ID)
client.tls_set(
    ca_certs=CA_PATH,
    certfile=CERT_PATH,
    keyfile=KEY_PATH
)
client.on_connect = on_connect
client.on_disconnect = on_disconnect

if not connect_with_retry(client, MQTT_BROKER, MQTT_PORT):
    print(f"[{DEVICE_ID}] Could not connect to broker. Exiting.")
    exit(1)

client.loop_start()

print(f"[{DEVICE_ID}] Simulator started | Profile: {DEVICE_PROFILE} | Interval: {INTERVAL_MS}ms")

try:
    while True:
        data = generate_data()
        payload = json.dumps(data)
        try:
            client.publish(MQTT_TOPIC, payload, qos=1)
            print(f"[{DEVICE_ID}] Sent | Voltage: {data['voltage']}V | Frequency: {data['frequency']}Hz | Power Factor: {data['power_factor']}")
        except Exception as e:
            print(f"[{DEVICE_ID}] ERROR publishing message: {str(e)}")
        time.sleep(INTERVAL_MS / 1000)
except KeyboardInterrupt:
    print(f"[{DEVICE_ID}] Simulator stopped")
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print(f"[{DEVICE_ID}] ERROR: {str(e)}")
    client.loop_stop()
    client.disconnect()