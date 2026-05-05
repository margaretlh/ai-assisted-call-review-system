import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{Path(__file__).resolve().parent}/db.sqlite3",
)
DEBUG: bool = os.environ.get("DEBUG", "True") == "True"
