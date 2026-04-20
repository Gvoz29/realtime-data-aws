FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy simulator code
COPY simulator.py .

# Run simulator
CMD ["python", "simulator.py"]
