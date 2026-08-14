"""
passenger_wsgi.py
-----------------
Entry point for Hostinger Shared & Cloud Hosting (cPanel / hPanel 'Setup Python App').
CloudLinux Passenger requires a WSGI callable named 'application'.
We wrap FastAPI's ASGI application with a2wsgi's ASGIMiddleware.
"""

import sys
import os
from pathlib import Path

# Add project root directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Load environment variables if .env exists
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=BASE_DIR / ".env")
except ImportError:
    pass

# Import the FastAPI application
from server import app as asgi_app

try:
    from a2wsgi import ASGIMiddleware
    # CloudLinux Passenger expects a WSGI callable named 'application'
    application = ASGIMiddleware(asgi_app)
except ImportError:
    # Fallback to standard ASGI or uvicorn runner if a2wsgi is not yet installed
    application = asgi_app
