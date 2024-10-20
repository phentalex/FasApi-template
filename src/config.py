import logging
import os
from dotenv import load_dotenv

load_dotenv()

public_or_local = os.getenv("PUBLIC_OR_LOCAL", "LOCAL")

OPENALEX_API_URL = os.getenv('OPENALEX_API_URL', "https://api.openalex.org")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_SAVE_PATH = os.path.join(BASE_DIR, 'JSONsaves')
CSV_SAVE_PATH = os.path.join(BASE_DIR, 'CSVsaves')


logging.basicConfig(
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s", datefmt="%H:%M:%S", level=logging.ERROR,
)
logger = logging.getLogger("microservice indicators")
