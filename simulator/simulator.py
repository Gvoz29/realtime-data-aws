import random
import time
import json
import os
import signal
import paho.mqtt.client as mqtt

# Environment variables
DEVICE_ID = os.environ.get("DEVICE_ID", "device_dev_01")
DEVICE_TYPE = os.environ.get("DEVICE_TYPE", "SMART_METER")
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


def generate_data():
    # Default normal state
    data = {
        "device_id": DEVICE_ID,
        "device_type": DEVICE_TYPE,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "voltage": round(random.uniform(228, 232), 2),
        "frequency": round(random.uniform(49.98, 50.02), 3),
        "power_factor": round(random.uniform(0.95, 0.99), 2),
        "current": round(random.uniform(5, 15), 2)
    }

    chance = random.random()

    if DEVICE_TYPE == "PMU":
        # PMU - fast (100ms)
        # 40% dynamic grid oscillations
        if chance < 0.40:
            # Small voltage and frequency oscillations
            data["frequency"] = round(data["frequency"] + random.uniform(-0.15, 0.15), 3)
            data["voltage"] = round(data["voltage"] + random.uniform(-5, 5), 2)
        elif chance < 0.55:
            # Frequency instability - generator dropped off grid
            data["frequency"] = random.choice([
                round(random.uniform(48.5, 49.7), 3),  # too low
                round(random.uniform(50.3, 51.5), 3),  # too high
            ])
        elif chance < 0.65:
            # Voltage dip - heavy load on line
            data["voltage"] = round(random.uniform(207, 215), 2)

    elif DEVICE_TYPE == "RTU":
        # RTU - medium (500ms)
        # 20% serious grid events
        if chance < 0.08:
            # Phase loss - transformer fault
            data["voltage"] = 0
            data["current"] = 0    # no voltage → no current
            data["power_factor"] = 0
        elif chance < 0.15:
            # High voltage - transformer tap issue
            data["voltage"] = round(random.uniform(245, 260), 2)
            data["current"] = round(random.uniform(18, 25), 2)
        elif chance < 0.20:
            # Overcurrent - overloaded substation
            data["current"] = round(random.uniform(22, 35), 2)
            data["voltage"] = round(data["voltage"] - random.uniform(5, 12), 2)
            data["power_factor"] = round(random.uniform(0.78, 0.86), 2)

    elif DEVICE_TYPE == "SMART_METER":
        # SMART_METER - slow (2000ms)
        # 5% local overload events
        if chance < 0.03:
            # Local overload - too many devices
            data["current"] = round(random.uniform(25, 40), 2)
            data["voltage"] = round(data["voltage"] - random.uniform(8, 20), 2)
            data["power_factor"] = round(random.uniform(0.75, 0.85), 2)
        elif chance < 0.05:
            # Poor power factor - inductive loads (AC, fridge, motors)
            data["power_factor"] = round(random.uniform(0.65, 0.82), 2)
            data["current"] = round(random.uniform(12, 20), 2)

    # Calculate active power based on final values
    data["active_power"] = round(data["voltage"] * data["current"] * data["power_factor"], 2)

    return data

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

print(f"[{DEVICE_ID}] Simulator started | Interval: {INTERVAL_MS}ms")

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