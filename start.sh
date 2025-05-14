#!/bin/bash

# Print debugging information
echo "Environment variables:"
echo "PORT: $PORT"

# Convert PORT to integer if it exists, otherwise use 8501
if [ -z "$PORT" ]; then
  PORT_INT=8501
  echo "PORT not set, using default: $PORT_INT"
else
  PORT_INT=$PORT
  echo "Using PORT: $PORT_INT"
fi

# Export Streamlit-specific environment variables
export STREAMLIT_SERVER_PORT=$PORT_INT
export STREAMLIT_SERVER_ADDRESS="0.0.0.0"

# Export MCP server environment variables
export MCP_SERVER_HOST="localhost"
export MCP_SERVER_PORT="8080"

echo "STREAMLIT_SERVER_PORT: $STREAMLIT_SERVER_PORT"
echo "STREAMLIT_SERVER_ADDRESS: $STREAMLIT_SERVER_ADDRESS"
echo "MCP_SERVER_HOST: $MCP_SERVER_HOST"
echo "MCP_SERVER_PORT: $MCP_SERVER_PORT"

# Start MCP server in the background
echo "Starting MCP server..."
python tcp_mcp_server.py &
MCP_PID=$!

# Wait for MCP server to start
echo "Waiting for MCP server to start..."
sleep 5

# Start Streamlit app
echo "Starting Streamlit..."
exec streamlit run tcp_web_app.py