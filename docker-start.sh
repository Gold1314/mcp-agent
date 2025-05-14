#!/bin/bash

# Set Docker environment flag
export DOCKER_ENVIRONMENT=true

# Start MCP server in the background
echo "Starting MCP server..."
python tcp_mcp_server.py &
MCP_PID=$!

# Wait briefly for the MCP server to start
sleep 2

# Convert PORT to integer if it exists, otherwise use 8501
PORT_INT=${PORT:-8501}

# Export Streamlit-specific environment variables
export STREAMLIT_SERVER_PORT=$PORT_INT
export STREAMLIT_SERVER_ADDRESS="0.0.0.0"

# Run the application with streamlit
echo "Starting Streamlit..."
streamlit run tcp_web_app.py

# If streamlit exits, kill the MCP server
kill $MCP_PID