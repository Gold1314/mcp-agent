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

echo "STREAMLIT_SERVER_PORT: $STREAMLIT_SERVER_PORT"
echo "STREAMLIT_SERVER_ADDRESS: $STREAMLIT_SERVER_ADDRESS"

# Run the application directly with streamlit instead of through run.py
# This avoids any potential issues with the Python script
echo "Starting Streamlit..."
exec streamlit run web_app.py