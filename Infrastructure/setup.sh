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

