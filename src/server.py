from typing import Annotated, List

# import pandas as pd
import uvicorn
import json, csv, os
import httpx, requests
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

from src.config import logger, public_or_local
from src.models.valid_type_request import HellowRequest
from src.utils.greeting import hellow_names

if public_or_local == 'LOCAL':
    url = 'http://localhost'
else:
    url = 'http://11.11.11.11'

origins = [
    url
]

app = FastAPI(docs_url="/template_fast_api/v1/", openapi_url='/template_fast_api/v1/openapi.json')
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/template_fast_api/v1/greetings")
async def inputation(body: Annotated[
    HellowRequest, Body(
        example={"names": ['Sasha', 'Nikita', 'Kristina']})]):
    try:
        names = body.names
        if names:
            res = hellow_names(names)
            return res
        else:
            logger.error("Something happened during creation of the search table")
            raise HTTPException(
                status_code=400,
                detail="Bad Request",
                headers={"X-Error": "Something happened during creation of the search table"},
            )
    except Exception as ApplicationError:
        logger.error(ApplicationError.__repr__())
        raise HTTPException(
            status_code=400,
            detail="Unknown Error",
            headers={"X-Error": f"{ApplicationError.__repr__()}"},
        )

OPENALEX_API_URL = "https://api.openalex.org"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_SAVE_PATH = os.path.join(BASE_DIR, 'JSONsaves')
CSV_SAVE_PATH = os.path.join(BASE_DIR, 'CSVsaves')

def save_to_json(data, work_id):
    if not os.path.exists(JSON_SAVE_PATH):
        os.makedirs(JSON_SAVE_PATH)
    json_filename = os.path.join(JSON_SAVE_PATH, f"{work_id}.json")
    if not os.path.exists(json_filename):
        with open(json_filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)

def append_to_csv(data, work_id):
    if not os.path.exists(CSV_SAVE_PATH):
        os.makedirs(CSV_SAVE_PATH)
    csv_filename = os.path.join(CSV_SAVE_PATH, 'works.csv')
    
    file_exists = os.path.isfile(csv_filename)

    if file_exists:
        with open(csv_filename, 'r', newline='', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            if any(row[0] == work_id for row in reader):
                return

    with open(csv_filename, 'a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        
        if not file_exists:
            writer.writerow(data.keys())
        
        writer.writerow([work_id, *data.values()])

async def fetch_json(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

@app.get("/get-work/{id}")
async def get_work(id: str):
    id = id.upper() if id.lower().startswith("w") else f"W{id}"
    
    full_id = f"{OPENALEX_API_URL}/works/{id}"
    
    try:
        data = await fetch_json(full_id)
        
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
            "title": data.get("display_name")
        }
        
        save_to_json(work_data, id)
        append_to_csv(work_data, id)
        
        return work_data
    
    except httpx.HTTPStatusError as exc:
        return {"error": "OpenAlex API error", "status_code": exc.response.status_code, "detail": exc.response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the indicators System API"}


if __name__ == "__main__":
    port = 8080
    uvicorn.run(app, host="127.0.0.1", port=port)
