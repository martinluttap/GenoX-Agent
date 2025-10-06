FROM python:3.9-slim

# Install system dependencies in a single layer for better caching
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set working directory
WORKDIR /app

# Copy ONLY requirements first for better caching
# This layer will be cached unless requirements.txt changes
COPY requirements.txt .

# Upgrade pip first (separate layer for caching)
RUN pip install --no-cache-dir --upgrade pip

# Install Python dependencies (cached layer unless requirements.txt changes)
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip

# Copy the application code (this layer changes frequently)
COPY ssd-infernce.py .

# Create directories for outputs
RUN mkdir -p /app/data /app/logs

# Set environment variables for maximum performance
ENV PYTHONUNBUFFERED=1
# Use all available CPU threads (0 = auto-detect and use all)
ENV OMP_NUM_THREADS=0
ENV MKL_NUM_THREADS=0
ENV PYTORCH_NUM_THREADS=0
ENV NUMEXPR_NUM_THREADS=0

# Run the application
CMD ["python3", "ssd-infernce.py"]