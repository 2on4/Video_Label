import subprocess
import sys
from configparser import ConfigParser
import os

def install_dependencies():
    """Install dependencies from requirements.txt."""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

def setup_config():
    """Prompt for Gemini API key and create config.ini."""
    config = ConfigParser()
    api_key = input("Enter your Google Gemini API key: ").strip()
    if not api_key:
        print("API key is required.")
        sys.exit(1)
    
    config['gemini'] = {'api_key': api_key}
    config['paths'] = {'default_source': '', 'default_target': ''}
    config['settings'] = {'dry_run': 'True', 'max_workers': '10'}
    
    os.makedirs('config', exist_ok=True)
    with open('config/config.ini', 'w') as configfile:
        config.write(configfile)
    print("config.ini created successfully.")

if __name__ == "__main__":
    install_dependencies()
    setup_config() 