"""
GovPulse API — Configuration
"""

import os
from dotenv import load_dotenv


load_dotenv()


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

MAPPED_FILE    = os.path.join(DATA_DIR, "processed", "mapped.json")
RESPONSES_FILE = os.path.join(DATA_DIR, "processed", "responses.json")
APPROVALS_FILE = os.path.join(DATA_DIR, "processed", "approvals.json")
XLSX_FILE      = os.path.join(DATA_DIR, "processed", "daily_brief.xlsx")
PDF_FILE       = os.path.join(DATA_DIR, "processed", "daily_brief.pdf")
CONFIG_YAML    = os.path.join(PROJECT_ROOT, "app", "config.yaml")

# JWT
JWT_SECRET    = os.getenv("JWT_SECRET", "govpulse_dev_secret_change_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 8

# CORS — allow the frontend origin

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5500,http://localhost:3000"
).split(",")