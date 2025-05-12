FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libstdc++6 \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "web_app.py", "--server.port=8501", "--server.address=0.0.0.0"] 