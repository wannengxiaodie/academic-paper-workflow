import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, '..', 'backend')
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

from main import app
from mangum import Mangum

handler = Mangum(app, lifespan="off")
