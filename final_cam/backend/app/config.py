from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"

# Load this project's .env explicitly
load_dotenv(ENV_FILE, override=True)


def get_groq_api_key():
    return os.getenv("GROQ_API_KEY", "").strip()


def get_groq_model():
    return os.getenv(
        "GROQ_MODEL",
        "openai/gpt-oss-120b"
    ).strip()


def get_mca_api_key():
    return os.getenv("MCA_API_KEY", "").strip()


def get_mca_base_url():
    return os.getenv(
        "MCA_API_BASE_URL",
        "https://api.filesure.in"
    ).strip().rstrip("/")