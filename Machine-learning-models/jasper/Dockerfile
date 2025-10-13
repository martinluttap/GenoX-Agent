# Jasper Dockerfile (CPU-only, sample data)

FROM python:3.10-slim

# Set environment variables for faster, cleaner installs
ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	PIP_DISABLE_PIP_VERSION_CHECK=1 \
	PIP_PROGRESS_BAR=off

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary code and data
COPY jasper_complete.py ./
COPY sample_data/ sample_data/

# Default command: run throughput test
CMD ["python3", "jasper_complete.py", "--mode", "throughput_test"]
