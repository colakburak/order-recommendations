import logging

from datetime import date
from fastapi import FastAPI, UploadFile, File

from app.datasets import DATASETS, DatasetName
from app.recommendations import fetch_recommendations
from app.ingestion.loader import load
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
@app.post("/load/{dataset}", response_model=UploadResponse)
def upload(
    dataset: DatasetName,
    file: UploadFile = File(...)
) -> UploadResponse:
    content = file.file.read()
    metadata = load(content, str(file.filename), DATASETS[dataset])
    return UploadResponse(
        status="success",
        message=f"{dataset.label} uploaded successfully.",
        metadata=metadata
    )