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

# Install Python dependencies
RUN pip install --no-cache-dir numpy==1.26.4 pandas==2.0.0 && \
    pip install --no-cache-dir -r requirements.txt

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