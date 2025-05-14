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

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies in smaller chunks
RUN pip install --no-cache-dir numpy==1.26.4 && \
    pip install --no-cache-dir pandas==2.0.0 && \
    pip install --no-cache-dir streamlit==1.32.0 && \
    pip install --no-cache-dir yfinance==0.2.36 && \
    pip install --no-cache-dir plotly==5.0.0 && \
    pip install --no-cache-dir python-dotenv==1.0.0 && \
    pip install --no-cache-dir openai==1.0.0 && \
    pip install --no-cache-dir tornado==6.4 && \
    pip install --no-cache-dir asyncio==3.4.3 && \
    pip install --no-cache-dir langchain-mcp-adapters>=0.0.1 && \
    pip install --no-cache-dir langchain-openai>=0.0.5 && \
    pip install --no-cache-dir langgraph>=0.0.20 && \
    pip install --no-cache-dir fastmcp>=0.0.1

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 8501

# Command to run the application
CMD ["python", "run.py"] 