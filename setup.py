import os
import shutil
import subprocess
import sys

def setup_project():
    """Set up the Steve Appointment Booker project."""
    print("Setting up Steve Appointment Booker...")

    # Create necessary directories
    os.makedirs("backend/logs", exist_ok=True)
    os.makedirs("frontend/build", exist_ok=True)

    # Copy env.example to .env if it doesn't exist
    if not os.path.exists('.env'):
        shutil.copy('env.example', '.env')
        print("Created .env file from template")

    # Set up backend
    print("\nSetting up backend...")
    try:
        os.chdir('backend')
        
        # Create virtual environment
        if not os.path.exists('venv'):
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
            print("Created virtual environment")

        # Activate virtual environment and install requirements
        if os.name == 'nt':  # Windows
            activate_script = os.path.join('venv', 'Scripts', 'activate.bat')
            pip_path = os.path.join('venv', 'Scripts', 'pip')
        else:  # Unix
            activate_script = os.path.join('venv', 'bin', 'activate')
            pip_path = os.path.join('venv', 'bin', 'pip')

        if os.name == 'nt':
            subprocess.run([activate_script, '&&', pip_path, 'install', '-r', 'requirements.txt'], shell=True, check=True)
        else:
            subprocess.run(['source', activate_script, '&&', pip_path, 'install', '-r', 'requirements.txt'], shell=True, check=True)

        print("Installed backend dependencies")

        # Initialize database
        subprocess.run([sys.executable, 'init_db.py'], check=True)
        print("Initialized database")

        os.chdir('..')
    except subprocess.CalledProcessError as e:
        print(f"Error setting up backend: {e}")
        return False

    # Set up frontend
    print("\nSetting up frontend...")
    try:
        os.chdir('frontend')
        subprocess.run(['npm', 'install'], check=True)
        print("Installed frontend dependencies")
        os.chdir('..')
    except subprocess.CalledProcessError as e:
        print(f"Error setting up frontend: {e}")
        return False

    print("\nSetup completed successfully!")
    print("\nTo start the application:")
    print("1. Backend: cd backend && python app.py")
    print("2. Frontend: cd frontend && npm start")
    
    return True

if __name__ == '__main__':
    setup_project() 