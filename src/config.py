import logging
import os
import asyncio
from pathlib import Path
from fastapi import HTTPException
from dotenv import load_dotenv
import httpx, csv, json, re
from datetime import datetime

load_dotenv()

public_or_local = os.getenv("PUBLIC_OR_LOCAL", "LOCAL")

OPENALEX_API_URL = os.getenv('OPENALEX_API_URL', "https://api.openalex.org")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_SAVE_PATH = os.path.join(BASE_DIR, 'JSONsaves')
CSV_SAVE_PATH = "./CSVsaves"

MAX_FILE_SIZE = 100 * 1024 * 1024
MAX_ROWS = 100000
PROGRESS_FILE = "progress.json"
STOP_FLAG = "stop.flag"

def reset_stop_flag():
    if Path(STOP_FLAG).exists():
        Path(STOP_FLAG).unlink()

def save_state(start_id, end_id, current_id, batch_size):
    state = {
        "start_id": start_id,
        "end_id": end_id,
        "current_id": current_id,
        "batch_size": batch_size
    }
    with open(PROGRESS_FILE, "w") as file:
        json.dump(state, file)

def load_state():
    if not Path(PROGRESS_FILE).exists():
        raise HTTPException(status_code=400, detail="No saved state found. Please start parsing first.")
    with open(PROGRESS_FILE, "r") as file:
        return json.load(file)


def clear_state():
    if Path(PROGRESS_FILE).exists():
        Path(PROGRESS_FILE).unlink()

def get_last_json_file():
    if not os.path.exists(JSON_SAVE_PATH):
        return None

    files = [f for f in os.listdir(JSON_SAVE_PATH) if f.endswith('.json')]
    if not files:
        return None

    files.sort(key=lambda f: os.path.getmtime(os.path.join(JSON_SAVE_PATH, f)), reverse=True)
    return os.path.join(JSON_SAVE_PATH, files[0])


def count_entries_in_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return len(data) if isinstance(data, list) else 0


def append_to_json(data, work_id):
    if not os.path.exists(JSON_SAVE_PATH):
        os.makedirs(JSON_SAVE_PATH)

    if not str(work_id).startswith('W'):
        work_id = f'W{work_id}'

    last_file = get_last_json_file()
    if last_file:

        file_size = os.path.getsize(last_file)
        entry_count = count_entries_in_json(last_file)
        if file_size >= MAX_FILE_SIZE or entry_count >= MAX_ROWS:
            last_file = None 

    if not last_file:

        base_filename = datetime.now().strftime("%d_%m_%Y")
        index = 1
        new_file = os.path.join(JSON_SAVE_PATH, f"{base_filename}.json")
        while os.path.exists(new_file):
            new_file = os.path.join(JSON_SAVE_PATH, f"{base_filename}_{index}.json")
            index += 1
        last_file = new_file

        with open(last_file, 'w', encoding='utf-8') as json_file:
            json.dump([], json_file, ensure_ascii=False, indent=4)

    with open(last_file, 'r+', encoding='utf-8') as json_file:
        file_data = json.load(json_file)
        if any(entry.get('work_id') == work_id for entry in file_data):
            return 

        file_data.append({"work_id": work_id, **data})
        json_file.seek(0)
        json.dump(file_data, json_file, ensure_ascii=False, indent=4)
        json_file.truncate()


def get_latest_csv_file():
    if not os.path.exists(CSV_SAVE_PATH):
        os.makedirs(CSV_SAVE_PATH)

    csv_files = [
        os.path.join(CSV_SAVE_PATH, f) for f in os.listdir(CSV_SAVE_PATH) if f.endswith('.csv')
    ]
    if not csv_files:
        return None

    latest_file = max(csv_files, key=os.path.getmtime)
    return latest_file


def get_csv_row_count(filename):
    with open(filename, 'r', newline='', encoding='utf-8') as file:
        return sum(1 for _ in file) - 1 

def append_to_csv(data, work_id):
    if not os.path.exists(CSV_SAVE_PATH):
        os.makedirs(CSV_SAVE_PATH)

    if not str(work_id).startswith('W'):
        work_id = f'W{work_id}'

    last_file = get_latest_csv_file()
    if last_file:
        file_size = os.path.getsize(last_file)
        row_count = get_csv_row_count(last_file)
        if file_size >= MAX_FILE_SIZE or row_count >= MAX_ROWS:
            last_file = None 

    if not last_file:
        base_filename = datetime.now().strftime("%d_%m_%Y")
        index = 1
        new_file = os.path.join(CSV_SAVE_PATH, f"{base_filename}.csv")
        while os.path.exists(new_file):
            new_file = os.path.join(CSV_SAVE_PATH, f"{base_filename}_{index}.csv")
            index += 1
        last_file = new_file

    file_exists = os.path.isfile(last_file)
    if file_exists:
        with open(last_file, 'r', newline='', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            if any(row[0] == work_id for row in reader):
                return 

    with open(last_file, 'a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        if not file_exists:
            writer.writerow(['work_id', *data.keys()]) 
        writer.writerow([work_id, *data.values()])


async def fetch_json(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60)
        if response.status_code == 200:
            print(f"Fetched data for {url}")
            return response.json()
        else:
            print(f"Failed to fetch data for {url}, status code: {response.status_code}")
            response.raise_for_status()

def remove_latex_expressions(text):
    cleaned_text = re.sub(r'[\r\n$]', '', text)
    return cleaned_text

async def get_abstract_text(abstract_inverted_index: dict) -> str:
    word_index = []
    
    for word, indices in abstract_inverted_index.items():
        for index in indices:
            word_index.append((word, index))
    
    word_index = sorted(word_index, key=lambda x: x[1])
    abstract = ' '.join([word for word, _ in word_index])
    cleaned_abstract = remove_latex_expressions(abstract)
    
    return cleaned_abstract

async def fetch_work_data(work_id):
    """
    Запрашивает данные работы по ID.
    """
    full_id = f"{OPENALEX_API_URL}/works/{work_id}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(full_id)
            response.raise_for_status()
            data = response.json()

            raw_title = data.get("display_name", "")
            if raw_title is None:
                cleaned_title = "Untitled"
            else:
                cleaned_title = re.sub(r'<[^>]+>', '', raw_title)

            work_data = {
                "id": data.get("id"),
                "primary_location": data.get("primary_location"),
                "type": data.get("type"),
                "publication_year": data.get("publication_year"),
                "concepts": data.get("concepts"),
                "authorships": data.get("authorships"),
                "best_oa_location": data.get("best_oa_location"),
                "cited_by_count": data.get("cited_by_count"),
                "doi": data.get("doi"),
                "locations": data.get("locations"),
                "Keywords": data.get("keywords"),
                "title": cleaned_title
            }

            if 'abstract_inverted_index' in data:
                abstract_text = await get_abstract_text(data['abstract_inverted_index'])
            else:
                abstract_text = "Abstract not found for this work"

            work_data["abstract"] = abstract_text
            return work_data

    except httpx.HTTPStatusError as exc:
        return {"error": f"API error for {work_id}", "status_code": exc.response.status_code}
    except Exception as e:
        return {"error": f"Error for {work_id}: {str(e)}"}


async def fetch_and_save(ids_batch, batch_index):
    if not work_id.startswith('W'):
        work_id = f'W{work_id}'
    tasks = [fetch_work_data(work_id) for work_id in ids_batch]
    results = await asyncio.gather(*tasks)

    for work_data in results:
        if "error" not in work_data:
            append_to_json(work_data, work_data["id"])
            append_to_csv(work_data, work_data["id"])

    print(f"Batch {batch_index} saved. Total works: {len(results)}")

async def parse_works(start_id, end_id, batch_size):
    progress = load_progress()
    processed_ids = progress.get("processed_ids", [])
    failed_ids = progress.get("failed_ids", [])

    for current_id in range(start_id, end_id + 1, batch_size):
        if Path(STOP_FLAG).exists():
            log_action("stopped")
            print(f"Parsing stopped at ID {current_id}.")
            break

        batch_ids = range(current_id, min(current_id + batch_size, end_id + 1))
        for work_id in batch_ids:
            try:
                data = await fetch_json(f"{OPENALEX_API_URL}/works/W{work_id}")

                raw_title = data.get("display_name", "")
                if raw_title is None:
                    cleaned_title = "Untitled"
                else:
                    cleaned_title = re.sub(r'<[^>]+>', '', raw_title)

                work_data = {
                    "id": data.get("id"),
                    "primary_location": data.get("primary_location"),
                    "type": data.get("type"),
                    "publication_year": data.get("publication_year"),
                    "concepts": data.get("concepts"),
                    "authorships": data.get("authorships"),
                    "best_oa_location": data.get("best_oa_location"),
                    "cited_by_count": data.get("cited_by_count"),
                    "doi": data.get("doi"),
                    "locations": data.get("locations"),
                    "Keywords": data.get("keywords"),
                    "title": cleaned_title
                }
                if 'abstract_inverted_index' in data:
                    abstract_inverted_index = data['abstract_inverted_index']
                    abstract_text = await get_abstract_text(abstract_inverted_index)
                else:
                    abstract_text = "Abstract not found for this work"
                work_data["abstract"] = abstract_text

                append_to_csv(work_data, work_id)
                append_to_json(work_data, work_id)

                processed_ids.append(work_id)
            except Exception as e:
                failed_ids.append(work_id)
                logger.error(f"Error processing ID W{work_id}: {str(e)}")
        
        progress.update({
            "current_id": current_id + batch_size,
            "processed_ids": processed_ids,
            "failed_ids": failed_ids,
        })
        save_progress(progress)

    log_action("completed")
    print(f"Parsing completed from {start_id} to {end_id}.")
def generate_ids(start, end):
    return [f"W{id}" for id in range(start, end + 1)]

def load_progress():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "start_id": 0,
            "end_id": 0,
            "current_id": 0,
            "batch_size": 0,
            "processed_ids": [],
            "failed_ids": [],
            "last_action": "",
            "last_update": None,
        }

def save_progress(data):
    """
    Сохранение состояния в progress.json.
    """
    data["last_update"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def log_action(action):
    """
    Логирование действия в progress.json.
    """
    progress = load_progress()
    progress["last_action"] = action
    save_progress(progress)

def read_progress():
    """Чтение прогресса из файла"""
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return None

def update_progress(start_id, current_id, end_id, batch_size):
    """Обновление прогресса в файл"""
    progress_data = {
        "start_id": start_id,
        "current_id": current_id,
        "end_id": end_id,
        "batch_size": batch_size,
    }
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress_data, f, indent=4)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)
