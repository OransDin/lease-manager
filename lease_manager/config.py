import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://lease:leasepass@db:5432/lease")
APP_TITLE = "📦 Lease Manager"