from typing import Annotated, List

import uvicorn
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

@app.get("/")
async def read_root():
    return {"message": "Welcome to the parser System API"}


if __name__ == "__main__":
    port = 8081
    uvicorn.run(app, host="localhost", port=port)
