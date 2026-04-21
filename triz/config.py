import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "triz_knowledge.db"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
SERP_API_KEY = os.getenv("SERP_API_KEY", "")

MAX_ITERATIONS = 5
MIN_IDEALITY_THRESHOLD = 0.3
SIMILARITY_THRESHOLD = 0.6
