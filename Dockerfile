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

# Upgrade pip and install wheel and setuptools
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements file first
COPY requirements.txt .

# Install packages in optimized batches
RUN pip install --no-cache-dir numpy==1.26.4 pandas==2.0.0 && \
    pip install --no-cache-dir streamlit==1.32.0 yfinance==0.2.36 plotly==5.0.0 && \
    pip install --no-cache-dir python-dotenv==1.0.0 openai==1.0.0 tornado==6.4 && \
    pip install --no-cache-dir asyncio==3.4.3 langchain-mcp-adapters>=0.0.1 langchain-openai>=0.0.5 && \
    pip install --no-cache-dir langgraph>=0.0.20 fastmcp>=0.0.1

# Copy application files
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Expose the port (will be overridden by Railway)
EXPOSE ${PORT:-8501}

# Run the start script
CMD ["./start.sh"]