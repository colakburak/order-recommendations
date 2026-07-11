import logging

from datetime import date
from fastapi import FastAPI, UploadFile, File


from app.schemas import (
    RecommendationResponse,
    UploadResponse
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Order Rec API",
    version="1.0.0"
)

# Result Retrieval
@app.get("/stores/{store_id}/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    store_id: str,
    date: date
)-> RecommendationResponse:
    return RecommendationResponse(
        store_id=store_id,
        date=date,
        count=0,
        recommendations=[]
    )

# Data Ingestion
@app.post("/load/items", response_model=UploadResponse)
async def upload_items(
    file: UploadFile = File(...)
) -> UploadResponse:
    content = await file.read()
    return UploadResponse(status="Success", message="Items uploaded successfully.", metadata=None)

@app.post("/load/inventory", response_model=UploadResponse)
async def upload_inventory(
    file: UploadFile = File(...)
) -> UploadResponse:
    content = await file.read()
    return UploadResponse(status="Success", message="Inventory uploaded successfully.", metadata=None)

@app.post("/load/orderable_items", response_model=UploadResponse)
async def upload_orderable_items(
    file: UploadFile = File(...)
) -> UploadResponse:
    content = await file.read()
    return UploadResponse(status="Success", message="Orderable items uploaded successfully.", metadata=None)

@app.post("/load/recommendations", response_model=UploadResponse)
async def upload_recommendations(
    file: UploadFile = File(...)
) -> UploadResponse:
    content = await file.read()
    return UploadResponse(status="Success", message="Recommendations uploaded successfully.", metadata=None)