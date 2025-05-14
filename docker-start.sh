#!/bin/bash

# Print debugging information
echo "Environment variables:"
echo "PORT: $PORT"

# Set Docker environment flag
export DOCKER_ENVIRONMENT=true

# Start MCP server in the background
echo "Starting MCP server..."
python tcp_mcp_server.py &
MCP_PID=$!

# Wait for the MCP server to start
echo "Waiting for MCP server to initialize..."
sleep 5

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

echo "STREAMLIT_SERVER_PORT: $STREAMLIT_SERVER_PORT"
echo "STREAMLIT_SERVER_ADDRESS: $STREAMLIT_SERVER_ADDRESS"

# Run the application with streamlit
echo "Starting Streamlit..."
streamlit run tcp_web_app.py

# If streamlit exits, kill the MCP server
kill $MCP_PID