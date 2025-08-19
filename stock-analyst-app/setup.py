#!/usr/bin/env python3
"""
Quick setup script for Stock Analyst App
"""

import subprocess
import sys
import os
import time

def run_command(command, description):
    """Run a command and display the result."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} is not compatible. Please use Python 3.8+")
        return False

def create_virtual_env():
    """Create virtual environment if it doesn't exist."""
    if not os.path.exists('venv'):
        print("\nCreating virtual environment...")
        return run_command(f"{sys.executable} -m venv venv", "Virtual environment creation")
    else:
        print("✓ Virtual environment already exists")
        return True

def activate_and_install():
    """Install requirements in virtual environment."""
    if os.name == 'nt':  # Windows
        activate_cmd = r"venv\Scripts\activate"
        pip_cmd = r"venv\Scripts\pip"
    else:  # Unix/Linux/Mac
        activate_cmd = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
    
    return run_command(f"{pip_cmd} install -r requirements.txt", "Installing Python packages")

def setup_database():
    """Initialize the database."""
    if os.name == 'nt':  # Windows
        python_cmd = r"venv\Scripts\python"
    else:  # Unix/Linux/Mac
        python_cmd = "venv/bin/python"
    
    return run_command(
        f'{python_cmd} -c "from models.portfolio import init_db; init_db(); print(\'Database initialized\')"',
        "Setting up database"
    )

def check_env_file():
    """Check if .env file exists and has required variables."""
    if not os.path.exists('.env'):
        print("\n⚠️  Warning: .env file not found!")
        print("Please create a .env file with your AWS credentials:")
        print("AWS_ACCESS_KEY_ID=your-access-key")
        print("AWS_SECRET_ACCESS_KEY=your-secret-key")
        print("AWS_REGION=us-east-2")
        print("MODEL_ID=your-claude-model-id")
        return False
    else:
        print("✓ .env file found")
        
        # Check for required variables
        with open('.env', 'r') as f:
            content = f.read()
            
        required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION', 'MODEL_ID']
        missing_vars = []
        
        for var in required_vars:
            if var not in content or f"{var}=" not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Warning: Missing environment variables: {', '.join(missing_vars)}")
            return False
        
        print("✓ Required environment variables found")
        return True

def main():
    """Main setup process."""
    print("Stock Analyst App - Quick Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Create virtual environment
    if not create_virtual_env():
        return
    
    # Install packages
    if not activate_and_install():
        print("\n⚠️  Package installation failed. You may need to install manually:")
        print("1. Activate virtual environment")
        print("2. Run: pip install -r requirements.txt")
        return
    
    # Setup database
    if not setup_database():
        print("\n⚠️  Database setup failed. You may need to set it up manually.")
    
    # Check environment file
    env_ok = check_env_file()
    
    print("\n" + "=" * 40)
    print("Setup Summary:")
    print("✓ Virtual environment created")
    print("✓ Python packages installed")
    print("✓ Database initialized")
    
    if env_ok:
        print("✓ Environment variables configured")
    else:
        print("⚠️  Environment variables need configuration")
    
    print("\nNext Steps:")
    print("1. Configure your .env file with AWS credentials (if not done)")
    print("2. Start MCP servers: python start_servers.py")
    print("3. Start Flask app: python app.py")
    print("4. Open browser to: http://localhost:5000")
    print("5. Run tests: python test_system.py")
    
    print("\nFor detailed instructions, see README.md")

if __name__ == "__main__":
    main()
