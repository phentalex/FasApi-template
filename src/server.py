from typing import Annotated, List

import uvicorn
import httpx
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

from src.config import logger, public_or_local
from src.models.valid_type_request import HellowRequest, OpenAlexRequest, WorkRequest
from src.utils.greeting import hellow_names
from src.utils.save_fun import save_to_json, append_to_csv
from src.utils.api_calls import fetch_json
from config import JSON_SAVE_PATH, CSV_SAVE_PATH, OPENALEX_API_URL
from config import save_to_json, append_to_csv, fetch_json, get_abstract_text

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

@app.post("/get_works/")
async def get_works(body: Annotated[WorkRequest, Body(
        example={"work_ids": ["W2117692326", "W2502170112", "W0987654321"]}
    )]):
    if len(body.work_ids) > 50:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum number of IDs exceeded. No more than 50 allowed."
        )
    if len(body.work_ids) > 50:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum number of IDs exceeded. No more than 50 allowed."
        )
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
            
            if 'abstract_inverted_index' in data:
                abstract_inverted_index = data['abstract_inverted_index']
                abstract_text = await get_abstract_text(abstract_inverted_index)
            else:
                abstract_text = "Abstract not found for this work"
            
            work_data["abstract"] = abstract_text

            if 'abstract_inverted_index' in data:
                abstract_inverted_index = data['abstract_inverted_index']
                abstract_text = await get_abstract_text(abstract_inverted_index)
            else:
                abstract_text = "Abstract not found for this work"
            
            work_data["abstract"] = abstract_text

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
