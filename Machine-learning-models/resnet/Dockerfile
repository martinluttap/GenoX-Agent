FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY resnet-inference-only.py .

# Create data directory for datasets
RUN mkdir -p /app/data

# Run the benchmark
CMD ["python", "resnet-inference-only.py"]