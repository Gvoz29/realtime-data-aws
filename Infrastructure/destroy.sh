#!/bin/bash
# destroy.sh - briše AWS resurse koji koštaju

echo "Brisanje Kinesis streama..."
aws kinesis delete-stream \
  --stream-name elektroenergetika-stream

