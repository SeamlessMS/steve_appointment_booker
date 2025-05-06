import subprocess
import time
import json
import os
import sys
import requests
from pathlib import Path

# Directory paths
BACKEND_DIR = os.path.join(os.getcwd(), 'backend')
FRONTEND_DIR = os.path.join(os.getcwd(), 'frontend')
CONFIG_PATH = os.path.join(BACKEND_DIR, 'config.json')
NGROK_PATH = os.path.join(os.getcwd(), 'ngrok.exe')

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("Checking dependencies...")
    
    # Create npm-wrapper.ps1 if it doesn't exist
    npm_wrapper_path = os.path.join(os.getcwd(), 'npm-wrapper.ps1')
    if not os.path.exists(npm_wrapper_path):
        print("⚠️ npm-wrapper.ps1 not found. This might cause npm issues on Windows.")
    
    # Check if Python dependencies are installed
    try:
        print("Installing backend dependencies...")
        pip_process = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', os.path.join(BACKEND_DIR, 'requirements.txt')], 
                      check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ Backend dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing backend dependencies: {e}")
        print("Please run: pip install -r backend/requirements.txt")
        return False
    
    # Skip Node.js check as it is already installed on the system
    print("✅ Assuming Node.js and npm are already installed")
    
    # Check if frontend dependencies are installed
    if not os.path.exists(os.path.join(FRONTEND_DIR, 'node_modules')):
        print("Installing frontend dependencies...")
        try:
            # Use npm-wrapper.ps1 if available, otherwise fall back to npm
            if os.path.exists(npm_wrapper_path):
                npm_process = subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-File', npm_wrapper_path, 'install'], 
                                           cwd=FRONTEND_DIR, check=True, stdout=subprocess.PIPE)
            else:
                npm_process = subprocess.run(['npm', 'install'], cwd=FRONTEND_DIR, check=True, stdout=subprocess.PIPE)
            print("✅ Frontend dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error installing frontend dependencies: {e}")
            print("Please run: cd frontend && npm install")
            return False
    else:
        print("✅ Frontend dependencies already installed")
    
    # Check if ngrok exists
    if not os.path.exists(NGROK_PATH):
        print(f"❌ ngrok not found at {NGROK_PATH}")
        print("Please download ngrok from https://ngrok.com/download and place it in the root directory")
        check_ngrok = input("Do you want to continue without ngrok? (y/n): ").lower()
        if check_ngrok != 'y':
            return False
    else:
        print(f"✅ Found ngrok at {NGROK_PATH}")
    
    # Check if config.json exists
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ config.json not found at {CONFIG_PATH}")
        return False
    
    # Check API keys in config.json
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Check essential keys - add any that would cause errors if missing/invalid
        essential_keys = {
            'LLM_API_KEY': 'OpenAI API Key',
            'TWILIO_ACCOUNT_SID': 'Twilio Account SID',
            'TWILIO_AUTH_TOKEN': 'Twilio Auth Token',
            'TWILIO_PHONE_NUMBER': 'Twilio Phone Number'
        }
        
        missing_keys = []
        for key, name in essential_keys.items():
            if not config.get(key) or config.get(key) == "dummy":
                missing_keys.append(f"{name} ({key})")
        
        if missing_keys:
            print(f"⚠️ Warning: The following API keys need to be configured in {CONFIG_PATH}:")
            for key in missing_keys:
                print(f"  - {key}")
            print("The app may not function correctly without these keys.")
            
            check_continue = input("Do you want to continue without these keys? (y/n): ").lower()
            if check_continue != 'y':
                return False
    except Exception as e:
        print(f"❌ Error reading config.json: {e}")
        return False
    
    return True

def kill_process_by_port(port):
    """Kill process using a specific port (Windows-specific)"""
    try:
        # PowerShell compatible command
        find_pid_cmd = f'Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess'
        result = subprocess.run(['powershell', '-Command', find_pid_cmd], 
                                capture_output=True, text=True, check=False)
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip().isdigit():
                    kill_cmd = f'Stop-Process -Id {pid.strip()} -Force -ErrorAction SilentlyContinue'
                    subprocess.run(['powershell', '-Command', kill_cmd], check=False)
            print(f"✅ Killed processes using port {port}")
            return True
        else:
            print(f"No process found using port {port}")
            return True
    except Exception as e:
        print(f"⚠️ Warning: Could not kill process on port {port}: {e}")
        return False

def start_ngrok():
    """Start ngrok and return the public URL"""
    print('Starting ngrok on port 5001...')
    
    # Check if port 4040 (ngrok admin) is in use and kill the process
    kill_process_by_port(4040)
    
    # Start ngrok with subprocess.Popen for better compatibility
    try:
        # PowerShell-compatible command
        ngrok_proc = subprocess.Popen([NGROK_PATH, 'http', '5001'], 
                                     stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)
    except Exception as e:
        print(f"❌ Error starting ngrok: {e}")
        return None, None
    
    # Give ngrok time to start
    print("Waiting for ngrok to initialize...")
    for attempt in range(15):  # Try for up to 15 seconds
        time.sleep(1)
        try:
            tunnels = requests.get('http://localhost:4040/api/tunnels', timeout=2).json()['tunnels']
            https_tunnel = next((t for t in tunnels if t['public_url'].startswith('https')), None)
            if https_tunnel:
                ngrok_url = https_tunnel['public_url']
                print(f'✅ ngrok URL: {ngrok_url}')
                return ngrok_proc, ngrok_url
        except Exception:
            print(f"Waiting for ngrok... ({attempt+1}/15)")
            continue  # Keep trying
    
    # If we reach here, ngrok failed to start properly
    try:
        ngrok_proc.terminate()
    except:
        pass
    print('❌ Failed to start ngrok or get a tunnel URL')
    
    # Ask if the user wants to continue without ngrok
    check_continue = input("Do you want to continue without ngrok? Callbacks won't work. (y/n): ").lower()
    if check_continue == 'y':
        return None, "http://localhost:5001"  # Use localhost as fallback
    return None, None

def update_config(ngrok_url):
    """Update the CALLBACK_URL in config.json"""
    if not ngrok_url:
        print("⚠️ No ngrok URL available, skipping config update")
        return True
        
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Set webhook URL to the ngrok URL without adding /webhook
        # The backend code will add /webhook when needed
        config['CALLBACK_URL'] = ngrok_url
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print(f'✅ Updated CALLBACK_URL in config.json to {ngrok_url}')
        return True
    except Exception as e:
        print(f'❌ Error updating config.json: {e}')
        return False

def start_backend():
    """Start the Flask backend server"""
    print('Starting backend server...')
    
    # Kill any process using port 5001
    kill_process_by_port(5001)
    
    # Create the backend start script file
    backend_script_path = os.path.join(os.getcwd(), 'start_backend.ps1')
    with open(backend_script_path, 'w') as f:
        f.write(f'cd "{BACKEND_DIR}"\n')
        f.write(f'& "{sys.executable}" app.py\n')
    
    # Using PowerShell Start-Process for Windows compatibility
    try:
        # First approach: Use Start-Process
        backend_cmd = f'Start-Process -FilePath "powershell" -ArgumentList "-ExecutionPolicy Bypass -File {backend_script_path}" -WindowStyle Normal'
        subprocess.run(['powershell', '-Command', backend_cmd], check=True)
        print("✅ Backend server starting with PowerShell script")
    except Exception as e:
        print(f"⚠️ First backend start approach failed: {e}")
        try:
            # Alternative approach: Direct Python execution
            print("Trying alternative approach to start backend...")
            backend_proc = subprocess.Popen([sys.executable, 'app.py'], 
                                          cwd=BACKEND_DIR, 
                                          creationflags=subprocess.CREATE_NEW_CONSOLE)
            print("✅ Backend server starting with alternative method")
        except Exception as second_e:
            print(f"❌ Error starting backend: {second_e}")
            return None
    
    # Wait for backend to initialize
    print("Waiting for backend to initialize...")
    max_attempts = 30  # Increased timeout
    for attempt in range(max_attempts):
        time.sleep(1)
        try:
            response = requests.get('http://localhost:5001', timeout=2)
            print("✅ Backend server is running")
            return True
        except requests.exceptions.RequestException:
            if attempt < max_attempts - 1:
                print(f"Waiting for backend to start... ({attempt+1}/{max_attempts})")
            else:
                print("⚠️ Backend server might not be running properly, but we'll continue")
                check_continue = input("Backend server isn't responding. Continue anyway? (y/n): ").lower()
                if check_continue != 'y':
                    return False
                return True
    
    return True

def start_frontend():
    """Start the React frontend server"""
    print('Starting frontend (npm start)...')
    
    # Kill any process using port 3000
    kill_process_by_port(3000)
    
    # Check if npm-wrapper.ps1 exists
    npm_wrapper_path = os.path.join(os.getcwd(), 'npm-wrapper.ps1')
    
    # PowerShell-friendly command to start the frontend
    try:
        if os.path.exists(npm_wrapper_path):
            # Use npm-wrapper.ps1 for more reliable execution
            frontend_cmd = f'Start-Process -FilePath "powershell" -ArgumentList "-ExecutionPolicy Bypass -File {npm_wrapper_path} start" -WorkingDirectory "{FRONTEND_DIR}" -WindowStyle Normal'
        else:
            # Fall back to regular npm if wrapper doesn't exist
            frontend_cmd = f'Start-Process -FilePath "npm" -ArgumentList "start" -WorkingDirectory "{FRONTEND_DIR}" -WindowStyle Normal'
            
        subprocess.run(['powershell', '-Command', frontend_cmd], check=True)
        print("✅ Frontend starting (this may take a moment)")
        return True
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
        
        # Try an alternative approach if the first method fails
        try:
            print("Trying alternative approach to start frontend...")
            if os.path.exists(npm_wrapper_path):
                subprocess.Popen(['powershell', '-ExecutionPolicy', 'Bypass', '-File', npm_wrapper_path, 'start'], 
                               cwd=FRONTEND_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen(['npm', 'start'], cwd=FRONTEND_DIR, shell=True)
            print("✅ Frontend starting with alternative method")
            return True
        except Exception as second_e:
            print(f"❌ Alternative approach also failed: {second_e}")
            return False

def main():
    """Main function to start all components"""
    print("\n=== Steve Appointment Booker Startup ===\n")
    
    # Create process cleanup script
    cleanup_script = os.path.join(os.getcwd(), 'cleanup.ps1')
    with open(cleanup_script, 'w') as f:
        f.write('# Cleanup script for Steve Appointment Booker\n')
        f.write('Write-Host "Cleaning up processes..."\n')
        f.write('Get-Process -Name ngrok -ErrorAction SilentlyContinue | Stop-Process -Force\n')
        f.write('Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force\n')
        f.write('Get-Process -Name Python -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -eq \'\'} | Stop-Process -Force\n')
        f.write('Write-Host "Cleanup complete."\n')
    
    print(f"✅ Created cleanup script at {cleanup_script}")
    
    # Step 1: Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please resolve the issues above and try again.")
        return
    
    # Step 2: Start ngrok if available
    ngrok_proc = None
    ngrok_url = None
    if os.path.exists(NGROK_PATH):
        ngrok_proc, ngrok_url = start_ngrok()
        if not ngrok_url and ngrok_url != "http://localhost:5001":
            print("\n❌ Failed to start ngrok. Please check your internet connection and try again.")
            return
    else:
        ngrok_url = "http://localhost:5001"
        print("⚠️ Running without ngrok - external callbacks won't work")
    
    # Step 3: Update config.json with the ngrok URL
    if not update_config(ngrok_url):
        print("\n❌ Failed to update config.json. Please check file permissions and try again.")
        if ngrok_proc:
            try:
                ngrok_proc.terminate()
            except:
                pass
        return
    
    # Step 4: Start the backend server
    backend_started = start_backend()
    if not backend_started:
        print("\n❌ Failed to start backend server. Please check the logs for errors.")
        if ngrok_proc:
            try:
                ngrok_proc.terminate()
            except:
                pass
        return
    
    # Wait a bit more to ensure the backend is fully initialized
    print("Ensuring backend is fully initialized...")
    time.sleep(3)
    
    # Step 5: Start the frontend
    frontend_started = start_frontend()
    if not frontend_started:
        print("\n❌ Failed to start frontend. Please check the logs for errors.")
        if ngrok_proc:
            try:
                ngrok_proc.terminate()
            except:
                pass
        return
    
    print('\n=== App is running! ===')
    print(f'- Backend (API): http://localhost:5001')
    if ngrok_url:
        print(f'- Backend (webhook): {ngrok_url}/webhook')
    print('- Frontend: http://localhost:3000')
    print('\n=== Testing ===')
    print('To run comprehensive tests:')
    print('  python -m tests.run_tests')
    print('To test calls with specific phone number:')
    print('  python -m tests.run_tests --test system --phone YOUR_PHONE_NUMBER')
    print('Or use individual test scripts:')
    print('  python make_test_call.py --phone YOUR_PHONE_NUMBER')
    print('  python fix_and_call.py --phone YOUR_PHONE_NUMBER')
    print('\n=== Stopping ===')
    print('To stop the app:')
    print('1. Press Ctrl+C in this terminal')
    print('2. Run this command to stop all services:')
    print(f'   powershell -ExecutionPolicy Bypass -File {cleanup_script}')
    
    # Keep the script running until Ctrl+C
    try:
        print("\nPress Ctrl+C to exit...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"\nError occurred: {e}")
    finally:
        print("Exiting. You may need to manually kill the processes.")

if __name__ == "__main__":
    main() 