import logging
import os
from dotenv import load_dotenv
import httpx, csv, json, re
from datetime import datetime

load_dotenv()

public_or_local = os.getenv("PUBLIC_OR_LOCAL", "LOCAL")

OPENALEX_API_URL = os.getenv('OPENALEX_API_URL', "https://api.openalex.org")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_SAVE_PATH = os.path.join(BASE_DIR, 'JSONsaves')
CSV_SAVE_PATH = os.path.join(BASE_DIR, 'CSVsaves')

MAX_FILE_SIZE = 100 * 1024 * 1024


def append_to_json(data, work_id):
    if not os.path.exists(JSON_SAVE_PATH):
        os.makedirs(JSON_SAVE_PATH)

    base_filename = datetime.now().strftime("%d_%m_%Y")
    json_filename = os.path.join(JSON_SAVE_PATH, f"{base_filename}.json")

    if os.path.exists(json_filename) and os.path.getsize(json_filename) >= MAX_FILE_SIZE:
        date_str = datetime.now().strftime("%d_%m_%Y")
        file_index = 1
        json_filename = os.path.join(JSON_SAVE_PATH, f"{base_filename}_{date_str}.json")
        while os.path.exists(json_filename):
            json_filename = os.path.join(JSON_SAVE_PATH, f"{base_filename}_{date_str}_{file_index}.json")
            file_index += 1

    if os.path.exists(json_filename):
        with open(json_filename, 'r', encoding='utf-8') as json_file:
            existing_data = json.load(json_file)
    else:
        existing_data = []

    if any(entry.get("work_id") == work_id for entry in existing_data):
        return

    existing_data.append({"work_id": work_id, **data})
    with open(json_filename, 'w', encoding='utf-8') as json_file:
        json.dump(existing_data, json_file, indent=4, ensure_ascii=False)


def append_to_csv(data, work_id):
    if not os.path.exists(CSV_SAVE_PATH):
        os.makedirs(CSV_SAVE_PATH)

    base_filename = datetime.now().strftime("%d_%m_%Y")
    csv_filename = os.path.join(CSV_SAVE_PATH, f"{base_filename}.csv")

    file_index = 1
    if os.path.exists(csv_filename) and os.path.getsize(csv_filename) >= MAX_FILE_SIZE:
        csv_filename = os.path.join(CSV_SAVE_PATH, f"{base_filename}_{file_index}.csv")
        file_index += 1

    file_exists = os.path.isfile(csv_filename)
    if file_exists:
        with open(csv_filename, 'r', newline='', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            if any(row[0] == work_id for row in reader):
                return 

    with open(csv_filename, 'a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        if not file_exists:
            writer.writerow(['work_id', *data.keys()])

        writer.writerow([work_id, *data.values()])

async def fetch_json(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

def remove_latex_expressions(text):
    cleaned_text1 = re.sub(r'\\n', '', text) #нужно переделать regex для "\n" 
    #cleaned_text2 = re.sub(r'\$', '', cleaned_text1)
    return cleaned_text1

async def get_abstract_text(abstract_inverted_index: dict) -> str:
    word_index = []
    
    for word, indices in abstract_inverted_index.items():
        for index in indices:
            word_index.append((word, index))
    
    word_index = sorted(word_index, key=lambda x: x[1])
    abstract = ' '.join([word for word, _ in word_index])
    cleaned_abstract = remove_latex_expressions(abstract)
    
    return cleaned_abstract

logging.basicConfig(
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s", datefmt="%H:%M:%S", level=logging.ERROR,
)
logger = logging.getLogger("microservice indicators")
