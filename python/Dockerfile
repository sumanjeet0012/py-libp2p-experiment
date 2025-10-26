# Use x86_64 platform because concrete-python doesn't have ARM64 wheels
FROM --platform=linux/amd64 python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY encrypted_credit_score_simple.py .

# Expose port
EXPOSE 5000

# Environment variables
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

# Run the server
CMD ["python", "encrypted_credit_score_simple.py"]
