import os
import subprocess
import sys

def main():
    # Get port from environment variable or use default
    port = os.environ.get('PORT', '8501')
    
    # Ensure port is a valid integer
    try:
        port = int(port)
    except ValueError:
        print(f"Invalid port number: {port}")
        sys.exit(1)
    
    # Set Streamlit environment variables
    os.environ['STREAMLIT_SERVER_PORT'] = str(port)
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
    
    # Run Streamlit
    subprocess.run(['streamlit', 'run', 'web_app.py'])

if __name__ == '__main__':
    main() 