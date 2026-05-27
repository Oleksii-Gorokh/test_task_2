import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./expeditions.db")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-goes-here-make-it-secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
