"""Config WSGI — expõe o callable ``app`` no nível do módulo (usado pelo gunicorn)."""

import os

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = get_wsgi_application()
