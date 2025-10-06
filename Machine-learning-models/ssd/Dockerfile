# Use PyTorch official image with pre-installed dependencies
# This includes torch, torchvision, numpy, and many ML libraries
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# Set working directory
WORKDIR /app

# Copy minimal requirements file (torch/torchvision already in base image)
COPY requirements-minimal.txt .

# Install only additional dependencies not in PyTorch base image
RUN pip install --no-cache-dir -r requirements-minimal.txt \
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