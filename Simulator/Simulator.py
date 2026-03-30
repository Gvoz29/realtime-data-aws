import requests
import random
import time
import json
import sys


API_URl= "http://localhost:5000/data"

SIMULATOR_ID = f"sim_{sys.argv[1]}"


def generate_data():
        return{

            "device_id": SIMULATOR_ID,
            "voltage": round(random.uniform(210,250),2),
            "current": round(random.uniform(5,20),2),
            "temperature": round(random.uniform(20,80),2),
            "timestamp": time.time()

        }

def send_data():
        data= generate_data()

        try:
            response= requests.post(API_URl, json=data)
            print(f"Sent: {data} | Status: {response.status_code}")
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    while True:
        send_data()
        time.sleep(1)