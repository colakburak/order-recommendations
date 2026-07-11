import logging
from fastapi import FastAPI, UploadFile, File

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
@app.get("/stores/{store_id}/recommendations")
async def get_recommendations(
    store_id: int,
    date: str
):
    return {"store_id": store_id, "date": date, "recommendations": ["item1", "item2", "item3"]}

# Data Ingestion
@app.post("/load/items")
async def upload_items(
    file: UploadFile = File(...)
):
    content = await file.read()
    return {"message": "Items uploaded successfully."}

@app.post("/load/inventory")
async def upload_inventory(
    file: UploadFile = File(...)
):
    content = await file.read()
    return {"message": "Inventory uploaded successfully."}

@app.post("/load/orderable_items")
async def upload_orderable_items(
    file: UploadFile = File(...)
):
    content = await file.read()
    return {"message": "Orderable items uploaded successfully."}

@app.post("/load/recommendations")
async def upload_recommendations(
    file: UploadFile = File(...)
):
    content = await file.read()
    return {"message": "Recommendations uploaded successfully."}