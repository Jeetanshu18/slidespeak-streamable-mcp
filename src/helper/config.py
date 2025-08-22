import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5001))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# SlideSpeak Configuration
SLIDESPEAK_API_KEY = os.getenv("SLIDESPEAK_API_KEY")
