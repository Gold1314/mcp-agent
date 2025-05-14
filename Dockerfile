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

# Install packages one by one with error handling
RUN pip install --no-cache-dir numpy==1.26.4 || echo "Failed to install numpy, continuing..." && \
    pip install --no-cache-dir pandas==2.0.0 || echo "Failed to install pandas, continuing..." && \
    pip install --no-cache-dir streamlit==1.32.0 || echo "Failed to install streamlit, continuing..." && \
    pip install --no-cache-dir yfinance==0.2.36 || echo "Failed to install yfinance, continuing..." && \
    pip install --no-cache-dir plotly==5.0.0 || echo "Failed to install plotly, continuing..." && \
    pip install --no-cache-dir python-dotenv==1.0.0 || echo "Failed to install python-dotenv, continuing..." && \
    pip install --no-cache-dir openai==1.0.0 || echo "Failed to install openai, continuing..." && \
    pip install --no-cache-dir tornado==6.4 || echo "Failed to install tornado, continuing..." && \
    pip install --no-cache-dir asyncio==3.4.3 || echo "Failed to install asyncio, continuing..." && \
    pip install --no-cache-dir langchain-mcp-adapters>=0.0.1 || echo "Failed to install langchain-mcp-adapters, continuing..." && \
    pip install --no-cache-dir langchain-openai>=0.0.5 || echo "Failed to install langchain-openai, continuing..." && \
    pip install --no-cache-dir langgraph>=0.0.20 || echo "Failed to install langgraph, continuing..." && \
    pip install --no-cache-dir fastmcp>=0.0.1 || echo "Failed to install fastmcp, continuing..."

# Copy application files
COPY . .

# Create a script to start both the MCP server and Streamlit app
RUN echo '#!/bin/bash\n\
# Start MCP server in the background\n\
python tcp_mcp_server.py &\n\
# Wait for server to start\n\
sleep 5\n\
# Start Streamlit app\n\
streamlit run tcp_web_app.py\n\
' > start.sh && chmod +x start.sh

# Expose the port
EXPOSE 8501

# Run the start script
CMD ["./start.sh"]