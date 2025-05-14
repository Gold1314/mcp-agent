FROM python:3.11-slim

WORKDIR /app

# Install only essential build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Upgrade pip and setuptools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

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
COPY mcp_server.py .
COPY web_app.py .

# Create TCP versions
RUN sed 's/mcp.run(transport="stdio")/mcp.run(transport="tcp", host="0.0.0.0", port=5000)/g' mcp_server.py > tcp_mcp_server.py 

RUN sed -e 's/from mcp import ClientSession, StdioServerParameters/from mcp import ClientSession, TCPServerParameters/g' \
        -e 's/from mcp.client.stdio import stdio_client/from mcp.client.tcp import tcp_client/g' \
        -e 's/server_params = StdioServerParameters(/server_params = TCPServerParameters(/g' \
        -e 's/command="python",.*args=\["mcp_server.py"\],/host="0.0.0.0", port=5000,/g' \
        -e 's/stdio_client/tcp_client/g' web_app.py > tcp_web_app.py

# Create startup script
RUN echo '#!/bin/bash\n\
# Start MCP server in background\n\
python tcp_mcp_server.py & \n\
PID=$!\n\
sleep 3\n\
# Set port for Streamlit\n\
export STREAMLIT_SERVER_PORT=${PORT:-8501}\n\
export STREAMLIT_SERVER_ADDRESS="0.0.0.0"\n\
# Start Streamlit\n\
echo "Starting Streamlit..."\n\
streamlit run tcp_web_app.py\n\
# Kill the background process if Streamlit exits\n\
kill $PID\n' > start.sh && chmod +x start.sh

# Create empty .env file
RUN touch .env

# Command to run the application
CMD ["bash", "./start.sh"]