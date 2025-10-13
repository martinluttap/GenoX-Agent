# Dockerfile for TFT model



# Use slim Python base image and install PyTorch via pip
FROM python:3.10-slim

# Reduce image size by cleaning up after install
WORKDIR /app

# Install system dependencies and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && pip cache purge

# Copy only necessary source code (avoid .git, __pycache__, etc.)
COPY . .

# Copy entrypoint script and make it executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use entrypoint to set thread env vars dynamically
ENTRYPOINT ["/entrypoint.sh"]

# Default command (can be overridden)
CMD ["python3", "tft_complete.py", "--mode", "throughput", "--dataset", "electricity", "--data_path", "./data/processed/electricity", "--epochs", "5", "--batch_size", "32", "--save_dir", "./checkpoints"]
