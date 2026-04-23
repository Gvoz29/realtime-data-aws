import json
import base64
import boto3
import logging
from datetime import datetime

# Logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')
table = dynamodb.Table('Merenja')

# Alarm thresholds
VOLTAGE_MIN = 207
VOLTAGE_MAX = 253
FREQUENCY_MIN = 49.8
FREQUENCY_MAX = 50.2
POWER_FACTOR_MIN = 0.85
CURRENT_MAX = 20

def check_alarms(measurement):
    alarms = []
    device_id = measurement['device_id']

    if measurement['voltage'] == 0:
        alarms.append({
            "type": "PHASE_LOSS",
            "message": f"Phase loss detected on {device_id}",
            "value": measurement['voltage']
        })
    elif measurement['voltage'] < VOLTAGE_MIN:
        alarms.append({
            "type": "VOLTAGE_LOW",
            "message": f"Low voltage on {device_id}: {measurement['voltage']}V",
            "value": measurement['voltage']
        })
    elif measurement['voltage'] > VOLTAGE_MAX:
        alarms.append({
            "type": "VOLTAGE_HIGH",
            "message": f"High voltage on {device_id}: {measurement['voltage']}V",
            "value": measurement['voltage']
        })

    if measurement['frequency'] < FREQUENCY_MIN:
        alarms.append({
            "type": "FREQUENCY_LOW",
            "message": f"Low frequency on {device_id}: {measurement['frequency']}Hz",
            "value": measurement['frequency']
        })
    elif measurement['frequency'] > FREQUENCY_MAX:
        alarms.append({
            "type": "FREQUENCY_HIGH",
            "message": f"High frequency on {device_id}: {measurement['frequency']}Hz",
            "value": measurement['frequency']
        })

    if measurement['current'] > CURRENT_MAX:
        alarms.append({
            "type": "OVERCURRENT",
            "message": f"Overcurrent on {device_id}: {measurement['current']}A",
            "value": measurement['current']
        })

    if measurement['power_factor'] < POWER_FACTOR_MIN:
        alarms.append({
            "type": "POOR_POWER_FACTOR",
            "message": f"Poor power factor on {device_id}: {measurement['power_factor']}",
            "value": measurement['power_factor']
        })

    return alarms

def save_to_dynamodb(measurement, alarms):
    try:
        item = {
            'device_id': measurement['device_id'],
            'timestamp': measurement['timestamp'],
            'device_type': measurement['device_type'],
            'voltage': str(measurement['voltage']),
            'current': str(measurement['current']),
            'frequency': str(measurement['frequency']),
            'power_factor': str(measurement['power_factor']),
            'active_power': str(measurement['active_power']),
            'has_alarm': len(alarms) > 0,
            'alarms': [alarm['type'] for alarm in alarms]
        }

        table.put_item(Item=item)
        logger.info(f"Saved to DynamoDB: {measurement['device_id']}")

    except Exception as e:
        logger.error(f"DynamoDB error: {str(e)}")
        raise

def publish_metrics(measurement, alarms):
    try:
        device_id = measurement['device_id']

        metric_data = [
            {
                'MetricName': 'Voltage',
                'Dimensions': [{'Name': 'DeviceId', 'Value': device_id}],
                'Value': measurement['voltage'],
                'Unit': 'None'
            },
            {
                'MetricName': 'Frequency',
                'Dimensions': [{'Name': 'DeviceId', 'Value': device_id}],
                'Value': measurement['frequency'],
                'Unit': 'None'
            },
            {
                'MetricName': 'Current',
                'Dimensions': [{'Name': 'DeviceId', 'Value': device_id}],
                'Value': measurement['current'],
                'Unit': 'None'
            },
            {
                'MetricName': 'PowerFactor',
                'Dimensions': [{'Name': 'DeviceId', 'Value': device_id}],
                'Value': measurement['power_factor'],
                'Unit': 'None'
            },
            {
                'MetricName': 'ActivePower',
                'Dimensions': [{'Name': 'DeviceId', 'Value': device_id}],
                'Value': measurement['active_power'],
                'Unit': 'None'
            },
            {
                'MetricName': 'AlarmCount',
                'Dimensions': [{'Name': 'DeviceId', 'Value': device_id}],
                'Value': len(alarms),
                'Unit': 'Count'
            }
        ]

        for alarm in alarms:
            metric_data.append({
                'MetricName': 'AlarmType',
                'Dimensions': [
                    {'Name': 'DeviceId', 'Value': device_id},
                    {'Name': 'AlarmType', 'Value': alarm['type']}
                ],
                'Value': 1,
                'Unit': 'Count'
            })

        cloudwatch.put_metric_data(
            Namespace='PowerGrid',
            MetricData=metric_data
        )

        logger.info(f"Metrics published for: {device_id}")

    except Exception as e:
        logger.error(f"CloudWatch error: {str(e)}")

def process_measurement(measurement):
    device_id = measurement['device_id']

    try:
        alarms = check_alarms(measurement)

        if alarms:
            alarm_types = [a['type'] for a in alarms]
            logger.warning(f"ALARM [{device_id}]: {alarm_types}")
        else:
            logger.info(f"OK [{device_id}] | "
                       f"Voltage: {measurement['voltage']}V | "
                       f"Frequency: {measurement['frequency']}Hz | "
                       f"Current: {measurement['current']}A | "
                       f"Power Factor: {measurement['power_factor']}")

        save_to_dynamodb(measurement, alarms)
        publish_metrics(measurement, alarms)

    except Exception as e:
        logger.error(f"Error processing measurement from {device_id}: {str(e)}")
        raise

def handler(event, context):
    logger.info(f"Lambda invoked - records: {len(event['Records'])}")

    for record in event['Records']:
        try:
            raw_data = base64.b64decode(record['kinesis']['data'])
            measurement = json.loads(raw_data)
            process_measurement(measurement)
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")

    return {"statusCode": 200, "body": "OK"}