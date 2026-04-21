#!/bin/bash
# setup.sh - kreira celu AWS infrastrukturu za diplomski

echo "Kreiranje IAM Role za Lambda..."
aws iam create-role \
  --role-name LambdaElektroenergetikaRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

echo "Dodavanje permisija na Role..."
aws iam attach-role-policy \
  --role-name LambdaElektroenergetikaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name LambdaElektroenergetikaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonKinesisReadOnlyAccess

aws iam attach-role-policy \
  --role-name LambdaElektroenergetikaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam attach-role-policy \
  --role-name LambdaElektroenergetikaRole \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess

echo "Kreiranje DynamoDB tabele..."
aws dynamodb create-table \
  --table-name Merenja \
  --attribute-definitions \
    AttributeName=device_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=device_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

echo "Kreiranje Kinesis streama..."
aws kinesis create-stream \
  --stream-name elektroenergetika-stream \
  --shard-count 1

  echo "Kreiranje IoT Policy..."
aws iot create-policy \
  --policy-name PowerGridDevicePolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "iot:Connect",
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": "iot:Publish",
        "Resource": "*"
      }
    ]
  }'

  echo "Kreiranje IoT Thing..."
aws iot create-thing \
  --thing-name PowerGridSimulator

echo "Kreiranje sertifikata..."
mkdir -p simulator/certs
aws iot create-keys-and-certificate \
  --set-as-active \
  --certificate-pem-outfile "simulator/certs/certificate.pem" \
  --public-key-outfile "simulator/certs/public.key" \
  --private-key-outfile "simulator/certs/private.key"

  echo "Povezivanje sertifikata sa Policy-em i Thing-om..."
CERT_ARN=$(aws iot list-certificates --query 'certificates[0].certificateArn' --output text)

aws iot attach-policy \
  --policy-name PowerGridDevicePolicy \
  --target $CERT_ARN

aws iot attach-thing-principal \
  --thing-name PowerGridSimulator \
  --principal $CERT_ARN

echo "Certificate ARN: $CERT_ARN"

echo "IoT Core endpoint:"
aws iot describe-endpoint --endpoint-type iot:Data-ATS
