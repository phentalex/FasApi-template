from typing import Annotated, List
import httpx, re, uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

from src.config import logger, public_or_local
from src.models.valid_type_request import HellowRequest, OpenAlexRequest, WorkRequest
from config import append_to_json, append_to_csv, fetch_json, get_abstract_text, OPENALEX_API_URL

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

@app.post("/get_works/")
async def get_works(body: Annotated[WorkRequest, Body(
        example={"work_ids": ["W2106096361", "W2036113194", "W4211007335", "W1686810756", "W2097706568", "W2101234009", "W2167590372",
                              "W2117692326", "W1522301498", "W2230728100", "W4297081765", "W2298230951", "W2106787323", "W2101108802",
                              "W2167279371", "W2163815564", "W2029667189", "W2108234281", "W2125435699", "W4294215472", "W2099540110",
                              "W1987258130", "W2114918609", "W1791587663", "W2151103935", "W2108598243", "W2103441770", "W2131271579",
                              "W4235678817", "W2112778345", "W2086957099", "W4385245566", "W3023540311", "W2135943618", "W2087484885",
                              "W2329395632", "W2912565176", "W2112796928", "W1968834637", "W3001118548", "W2030976617", "W2152311269",
                              "W2018289835", "W2157823046", "W2120062331", "W2170551349", "W1562208008", "W2142635246", "W1979300931",
                              "W2011039300"]}
    )]):
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
            ##
            if 'abstract_inverted_index' in data:
                abstract_inverted_index = data['abstract_inverted_index']
                abstract_text = await get_abstract_text(abstract_inverted_index)
            else:
                abstract_text = "Abstract not found for this work"
            ##
            work_data["abstract"] = abstract_text

            append_to_json(work_data, id)
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
