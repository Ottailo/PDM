import sys
import os
import traceback

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from app import create_app
    print("Attempting to create app...")
    app = create_app()
    print(f"App created successfully: {app}")
except Exception as e:
    print("Failed to create app:")
    traceback.print_exc()
