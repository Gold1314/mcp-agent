import os
import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Get port from environment variable or use default
    port_str = os.environ.get('PORT', '8501')
    logger.info(f"PORT environment variable: {port_str}")
    
    # Ensure port is a valid integer
    try:
        port = int(port_str)
        logger.info(f"Port converted to integer: {port}")
    except ValueError:
        logger.error(f"Invalid port number: {port_str}, using default 8501")
        port = 8501
    
    # Set Streamlit environment variables
    os.environ['STREAMLIT_SERVER_PORT'] = str(port)
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
    logger.info(f"Setting STREAMLIT_SERVER_PORT={os.environ['STREAMLIT_SERVER_PORT']}")
    logger.info(f"Setting STREAMLIT_SERVER_ADDRESS={os.environ['STREAMLIT_SERVER_ADDRESS']}")
    
    # Run Streamlit
    logger.info("Starting Streamlit app...")
    try:
        subprocess.run(['streamlit', 'run', 'web_app.py'], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running Streamlit: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    logger.info("Starting run.py")
    main()