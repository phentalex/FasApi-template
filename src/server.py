from typing import Annotated, List

import uvicorn
import re
import json, csv, os
import httpx, requests
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

from src.config import logger, public_or_local
from src.models.valid_type_request import HellowRequest, OpenAlexRequest
from src.utils.greeting import hellow_names
from src.utils.save_fun import save_to_json, append_to_csv
from src.utils.api_calls import fetch_json
from config import JSON_SAVE_PATH, CSV_SAVE_PATH

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


@app.post("/template_fast_api/v1/get_works")
async def inputation(body: Annotated[
    OpenAlexRequest, Body(
        example={"ids": ['W144423133', 'W2117692326', 'W2167279371']})]):
    path_json = JSON_SAVE_PATH
    path_to_csv = CSV_SAVE_PATH
    try:
        ids = body.ids
        if ids:
            works = await fetch_json(ids)
            for id, data in works.items():
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

                save_to_json(data=work_data, work_id=id, path=path_json)
                append_to_csv(data=work_data, work_id=id, path=path_to_csv)
            return works
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

class WorkRequest(BaseModel):
    work_ids: list[str]

    class Config:
        json_schema_extra = {
            "example": {
                "work_ids": ["W2117692326", "W1234567890", "W0987654321"]
            }
        }

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
        response = await client.get(url, timeout=20)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

def remove_latex_expressions(text):
    latex_pattern = r'\$'
    cleaned_text = re.sub(latex_pattern, '', text)

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

@app.get("/get_work_abstract/{id}")
async def get_work_abstract(id: str):
    id = id.upper() if id.lower().startswith("w") else f"W{id}"
    full_id = f"{OPENALEX_API_URL}/works/{id}"

    try:
        data = await fetch_json(full_id)
        
        if 'abstract_inverted_index' in data:
            abstract_inverted_index = data['abstract_inverted_index']
            abstract_text = await get_abstract_text(abstract_inverted_index)
            return {"abstract": abstract_text}
        else:
            return {"error": "Abstract not found for this work"}
    
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail="Error fetching data from OpenAlex")

@app.post("/get_works/")
async def get_works(body: Annotated[WorkRequest, Body(
        example={"work_ids": ["W2117692326", "W2502170112", "W0987654321"]}
    )]):
    results = []
    for id in body.work_ids:
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
            
            results.append(work_data)
        
        except httpx.HTTPStatusError as exc:
            results.append({"error": "OpenAlex API error", "status_code": exc.response.status_code, "detail": exc.response.text})
        except Exception as e:
            results.append({"error": f"Internal server error: {str(e)}"})

    return results

@app.get("/")
async def read_root():
    return {"message": "Welcome to the parser System API"}


if __name__ == "__main__":
    port = 8081
    uvicorn.run(app, host="localhost", port=port)
