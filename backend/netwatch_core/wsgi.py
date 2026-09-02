import os
import sys
from pathlib import Path
from django.core.wsgi import get_wsgi_application

# Ensure backend directory and its parent are in sys.path for robust imports across all deployment platforms
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netwatch_core.settings')

application = get_wsgi_application()
