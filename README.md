# Real-Time Power Grid Data Processing — AWS

> Thesis project: *Optimization of Real-Time Data Processing in Power Systems Using AWS Lambda*  
> Faculty of Technical Sciences, Novi Sad · 2025–2026

---

## Overview

A serverless, event-driven architecture for real-time monitoring of a simulated power grid. Ten containerized IoT devices (PMU, RTU, Smart Meters) continuously send measurements over MQTT to AWS IoT Core, which forwards the data stream through Kinesis into AWS Lambda for processing, anomaly detection, and storage.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                           │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────────────────┐   │
│  │   PMU    │  │   RTU    │  │     Smart Meter × 8         │   │
│  │ 100ms    │  │ 500ms    │  │        2000ms               │   │
│  └────┬─────┘  └────┬─────┘  └──────────────┬──────────────┘   │
└───────┼─────────────┼────────────────────────┼─────────────────┘
        │             │                        │
        └─────────────┴────────────────────────┘
                            │ MQTT TLS (port 8883)
                            ▼
                   ┌─────────────────┐
                   │  AWS IoT Core   │
                   │  X.509 auth     │
                   └────────┬────────┘
                            │ IoT Rule
                            ▼
                   ┌─────────────────┐
                   │    Kinesis      │
                   │  Data Streams   │
                   │   1 shard       │
                   └────────┬────────┘
                            │ trigger
                            ▼
                   ┌─────────────────┐
                   │  AWS Lambda     │
                   │  PowerGrid      │
                   │  Processor      │
                   └────────┬────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     ┌─────────────────┐       ┌─────────────────┐
     │    DynamoDB     │       │   CloudWatch    │
     │  Table: Merenja │       │  Namespace:     │
     │  PK: device_id  │       │  PowerGrid      │
     │  SK: timestamp  │       └─────────────────┘
     └─────────────────┘
```

---

## Device Types

| Device | Type | Interval | Anomaly Behavior |
|--------|------|----------|-----------------|
| `device_pmu_01` | PMU | 100ms | Dynamic voltage & frequency oscillations, frequency instability |
| `device_rtu_01` | RTU | 500ms | Phase loss, high voltage, overcurrent |
| `device_sm_01..08` | SMART_METER | 2000ms | Local overload, poor power factor |

---

## Alarm Thresholds

| Parameter | Normal Range | Alarm Type |
|-----------|-------------|------------|
| Voltage | 207V – 253V | `VOLTAGE_LOW` / `VOLTAGE_HIGH` |
| Voltage | 0V | `PHASE_LOSS` |
| Frequency | 49.8Hz – 50.2Hz | `FREQUENCY_LOW` / `FREQUENCY_HIGH` |
| Current | ≤ 20A | `OVERCURRENT` |
| Power Factor | ≥ 0.85 | `POOR_POWER_FACTOR` |

---

## Project Structure

```
realtime-data-aws/
├── simulator/
│   ├── simulator.py        # IoT device simulator
│   ├── requirements.txt    # paho-mqtt
│   └── Dockerfile
├── lambda/
│   ├── handler.py          # Lambda function
│   └── requirements.txt    # boto3
├── infrastructure/
│   ├── setup.sh            # Creates all AWS resources
│   └── destroy.sh          # Deletes Kinesis stream
├── docker-compose.yml      # 10 simulators configuration
└── .gitignore
```

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [AWS CLI](https://aws.amazon.com/cli/) configured with valid credentials
- AWS account (Free Tier is sufficient)

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Gvoz29/realtime-data-aws.git
cd realtime-data-aws
```

### 2. Create AWS infrastructure

```bash
chmod +x infrastructure/setup.sh
./infrastructure/setup.sh
```

This creates:
- IAM Role for Lambda (`LambdaElektroenergetikaRole`)
- DynamoDB table (`Merenja`)
- AWS IoT Core Thing, Policy, and certificates
- Kinesis Data Stream (`elektroenergetika-stream`)
- Lambda function (`PowerGridProcessor`)

### 3. Add IoT certificates

Download your IoT certificates from AWS IoT Core console and place them in:

```
simulator/certs/
├── certificate.pem
├── private.key
└── root-CA.crt
```

> **Note:** Certificates are excluded from version control via `.gitignore`. Never commit them to the repository.

### 4. Configure environment

Create a `.env` file in the project root:

```env
MQTT_BROKER=your-iot-endpoint.iot.eu-central-1.amazonaws.com
MQTT_PORT=8883
```

Find your IoT endpoint with:

```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS
```

### 5. Run the simulators

```bash
docker-compose up --build
```

All 10 simulators will start and begin sending measurements to AWS IoT Core.

---

## Stopping the System

```bash
# Stop simulators
docker-compose down

# Delete Kinesis stream (to avoid charges)
./infrastructure/destroy.sh
```

---

## AWS Services Used

| Service | Purpose | Cost |
|---------|---------|------|
| AWS IoT Core | MQTT broker, X.509 auth | Free Tier (250K msg/month) |
| Kinesis Data Streams | Real-time data buffering | ~$0.015/shard-hour |
| AWS Lambda | Stream processing & alarm detection | Free Tier (1M invocations/month) |
| DynamoDB | Measurements storage | Free Tier (25GB) |
| CloudWatch | Metrics, logs, dashboards | Free Tier (10 metrics) |

> **Tip:** Kinesis is the only paid service. Run `destroy.sh` after testing to avoid unnecessary charges.

---

## Monitoring

After the system is running, open the AWS CloudWatch console and navigate to **Metrics → PowerGrid** to view:

- Voltage, current, frequency, and power factor per device
- Alarm count and alarm type distribution
- Lambda invocation duration and error rates

---

## Author

**Branislav Gvozdenov**  
Faculty of Technical Sciences, Novi Sad  
[github.com/Gvoz29](https://github.com/Gvoz29)
