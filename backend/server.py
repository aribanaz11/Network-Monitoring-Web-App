#!/usr/bin/env python3
"""
NetWatch Enterprise Production WSGI Server
High-concurrency, multi-threaded production server using Waitress.
Serves both REST APIs and frontend assets seamlessly on all platforms.
"""

import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netwatch_core.settings')

import django
django.setup()

from django.core.wsgi import get_wsgi_application
from waitress import serve

application = get_wsgi_application()

def start_server():
    port = int(os.environ.get('PORT', 8000))
    print(f"\n" + "="*60)
    print(f"  NETWATCH PRODUCTION SERVER ONLINE (High-Concurrency)")
    print(f"  Listening on: http://127.0.0.1:{port} / http://0.0.0.0:{port}")
    print(f"  Workers / Threads: 8 Active Threads")
    print(f"="*60 + "\n")
    serve(application, host='0.0.0.0', port=port, threads=8)

if __name__ == '__main__':
    start_server()
