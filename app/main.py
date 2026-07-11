import logging

from datetime import date
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import JSONResponse

from app.ingestion.loaders import (
    InvalidCsvError,
    load_inventory,
    load_items,
    load_orderable_items,
    load_order_recommendations,
)
from app.recommendations import fetch_recommendations
from app.schemas import (
    RecommendationResponse,
    UploadResponse
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

app = FastAPI(
    title="Order Rec API",
    version="1.0.0"
)

@app.exception_handler(InvalidCsvError)
async def handle_invalid_csv(_request: Request, exc: InvalidCsvError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=UploadResponse(status="error", message=str(exc), metadata=None).model_dump(mode="json"),
    )

# Result Retrieval
@app.get("/stores/{store_id}/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    store_id: str,
    date: date
)-> RecommendationResponse:
    recommendations = fetch_recommendations(store_id, date)
    return RecommendationResponse(
        store_id=store_id,
        date=date,
        count=len(recommendations),
        recommendations=recommendations
    )

# Data Ingestion
@app.post("/load/items", response_model=UploadResponse)
async def upload_items(
    file: UploadFile = File(...)
) -> UploadResponse:
    content = await file.read()
    metadata = load_items(content, str(file.filename))
    return UploadResponse(status="success", message="Items uploaded successfully.", metadata=metadata)

@app.post("/load/inventory", response_model=UploadResponse)
async def upload_inventory(
    file: UploadFile = File(...)
) -> UploadResponse:
    content = await file.read()
    metadata = load_inventory(content, str(file.filename))
    return UploadResponse(status="success", message="Inventory uploaded successfully.", metadata=metadata)

@app.post("/load/orderable_items", response_model=UploadResponse)
async def upload_orderable_items(
    file: UploadFile = File(...)
) -> UploadResponse:
    content = await file.read()
    metadata = load_orderable_items(content, str(file.filename))
    return UploadResponse(status="success", message="Orderable items uploaded successfully.", metadata=metadata)

@app.post("/load/recommendations", response_model=UploadResponse)
async def upload_recommendations(
    file: UploadFile = File(...)
) -> UploadResponse:
    content = await file.read()
    metadata = load_order_recommendations(content, str(file.filename))
    return UploadResponse(status="success", message="Recommendations uploaded successfully.", metadata=metadata)