import os
import subprocess
import sys
import time
import webbrowser
from threading import Thread

def run_backend():
    """Run the backend server."""
    os.chdir('backend')
    if os.name == 'nt':  # Windows
        subprocess.run(['venv\\Scripts\\python', 'app.py'])
    else:  # Unix
        subprocess.run(['venv/bin/python', 'app.py'])

def run_frontend():
    """Run the frontend development server."""
    os.chdir('frontend')
    subprocess.run(['npm', 'start'])

def main():
    """Start both servers and open the application."""
    print("Starting Steve Appointment Booker...")
    
    # Check if setup is needed
    if not os.path.exists('backend/venv') or not os.path.exists('frontend/node_modules'):
        print("Initial setup required. Running setup script...")
        import setup
        if not setup.setup_project():
            print("Setup failed. Please check the errors above.")
            return

    # Start backend server in a separate thread
    backend_thread = Thread(target=run_backend)
    backend_thread.daemon = True
    backend_thread.start()
    
    # Wait for backend to start
    print("Starting backend server...")
    time.sleep(2)
    
    # Start frontend and open browser
    print("Starting frontend server...")
    run_frontend()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        sys.exit(0) 