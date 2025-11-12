import psycopg2
import psycopg2.extras
from .config import DB_URL

def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)