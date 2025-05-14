FROM python:3.11-slim

WORKDIR /app

# Install only essential build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY mcp_server.py .
COPY web_app.py .

# Create TCP versions
RUN sed 's/mcp.run(transport="stdio")/mcp.run(transport="tcp", host="0.0.0.0", port=5000)/g' mcp_server.py > tcp_mcp_server.py && \
    sed 's/from mcp import ClientSession, StdioServerParameters/from mcp import ClientSession, TCPServerParameters/g' web_app.py | \
    sed 's/from mcp.client.stdio import stdio_client/from mcp.client.tcp import tcp_client/g' | \
    sed 's/server_params = StdioServerParameters(/server_params = TCPServerParameters(/g' | \
    sed 's/command="python",\\n    args=\\["mcp_server.py"\\],/host="0.0.0.0", port=5000,/g' | \
    sed 's/stdio_client/tcp_client/g' > tcp_web_app.py

# Create startup script
RUN echo '#!/bin/bash\n\
# Start MCP server in background\n\
python tcp_mcp_server.py & \n\
sleep 2\n\
# Set port for Streamlit\n\
export STREAMLIT_SERVER_PORT=${PORT:-8501}\n\
export STREAMLIT_SERVER_ADDRESS="0.0.0.0"\n\
# Start Streamlit\n\
streamlit run tcp_web_app.py\n' > start.sh && chmod +x start.sh

# Create empty .env file
RUN touch .env

# Command to run the application
CMD ["./start.sh"]