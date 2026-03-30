from flask import Flask, request, jsonify
import json
import time

app = Flask(__name__)


data_log = []

# Постављамо праг аларма
CURRENT_THRESHOLD = 18.0   # ампери
TEMP_THRESHOLD = 70.0      # степени Ц

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    # Чување података у list
    data_log.append(data)

    # Чување у фајл за анализу
    with open("server_log.txt", "a") as f:
        f.write(json.dumps(data) + "\n")

    # Примитивни аларм
    alarms = []
    if data.get("current", 0) > CURRENT_THRESHOLD:
        alarms.append(f"High current: {data['current']} A")
    if data.get("temperature", 0) > TEMP_THRESHOLD:
        alarms.append(f"High temperature: {data['temperature']} °C")

    if alarms:
        print(f"ALARM! Device {data.get('device_id')}: {alarms}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)