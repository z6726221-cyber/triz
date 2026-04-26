import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "triz_knowledge.db"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

# Agent 独立配置（可选，不配置则回退到 OPENAI_* 和 MODEL_NAME）
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "")
AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "")
AGENT_MODEL_NAME = os.getenv("AGENT_MODEL_NAME", "")

# 各 Skill 可独立配置模型（如果不配置，默认使用 MODEL_NAME）
MODEL_M1 = os.getenv("MODEL_M1", MODEL_NAME)
MODEL_M2 = os.getenv("MODEL_M2", MODEL_NAME)
MODEL_M3 = os.getenv("MODEL_M3", MODEL_NAME)
MODEL_M5 = os.getenv("MODEL_M5", MODEL_NAME)
MODEL_M6 = os.getenv("MODEL_M6", MODEL_NAME)

SERP_API_KEY = os.getenv("SERP_API_KEY", "")

# FOS 缓存配置
FOS_CACHE_DIR = DATA_DIR / "fos_cache"
FOS_CACHE_TTL_HOURS = int(os.getenv("FOS_CACHE_TTL_HOURS", "168"))  # 默认7天

MAX_ITERATIONS = 5
MIN_IDEALITY_THRESHOLD = 0.3
SIMILARITY_THRESHOLD = 0.6

# API 重试配置
API_MAX_RETRIES = 5
API_BASE_DELAY = 3.0  # 初始重试延迟（秒），使用指数退避
