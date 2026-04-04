import random, time, json




def generate_data(device_num):
        device_type= "SMART_METER" if device_num<=500 else "RTU_PMU"
        return{
            

            "device_id": f"DEV_{device_num:03d}",
            "device_type": device_type,
            "voltage": round(random.uniform(210,250),2),
            "current": round(random.uniform(5,20),2),
            "temperature": round(random.uniform(20,80),2),
            "timestamp": time.time()

        }


if __name__ == "__main__":
    try:
        while True:

            batch= [generate_data(random.randint(1, 560)) for _ in range(100)]

            data= json.dumps(batch, ensure_ascii=False, indent=2)  
            print(data)
            time.sleep(random.uniform(0.1, 0.5))



    except KeyboardInterrupt:
         print("Kraj simulacije")        