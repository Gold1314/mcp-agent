FROM python:3.11-slim

# Set environment variables to reduce Python buffering and prevent bytecode generation
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies - combine RUN commands to reduce layers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies all at once to reduce layers and speed up the build
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary files for the TCP version
COPY tcp_mcp_server.py tcp_web_app.py docker-start.sh ./
COPY .env ./

# Make the start script executable
RUN chmod +x docker-start.sh

# Command to run the application
CMD ["bash", "docker-start.sh"]