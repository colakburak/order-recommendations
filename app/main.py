import logging
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Order Rec API",
    version="1.0.0"
)
