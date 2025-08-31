#!/usr/bin/env python3

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False

def run_streamlit():
    """Run the Streamlit application"""
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port=8501"])
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
    except Exception as e:
        print(f"❌ Error running application: {e}")

if __name__ == "__main__":
    print("🚀 Starting Stock Portfolio Manager...")
    
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found")
        sys.exit(1)
    
    print("📦 Installing/checking requirements...")
    if not install_requirements():
        print("❌ Failed to install requirements. Please install manually:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    print("🌐 Starting web application...")
    print("📈 Open your browser to http://localhost:8501")
    print("🛑 Press Ctrl+C to stop the application")
    
    run_streamlit()