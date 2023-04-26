from firebase_admin import firestore, credentials
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import logging, sys, json_logging, uvicorn, firebase_admin
from google.oauth2 import service_account
import RED_metrics
from prometheus_fastapi_instrumentator import Instrumentator


cred = credentials.Certificate('google-credentials.json')
credentials = service_account.Credentials.from_service_account_file('google-credentials.json')

app = FastAPI()
firebase_admin.initialize_app(cred)
db = firestore.Client(credentials=credentials)
json_logging.init_fastapi(enable_json=True)
json_logging.init_request_instrument(app)

# Instrument the app.
Instrumentator().instrument(app).expose(app)

# init the logger as usual
logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


class Item(BaseModel):
    id: Optional[str]
    name: str
    description: str
    price: float
    tax: float


@app.post("/items/")
async def create_item(request: Request, item: Item):
    doc_ref = db.collection("items").document()
    item_dict = item.dict()
    item_dict["id"] = doc_ref.id
    doc_ref.set(item_dict)
    item_id = doc_ref.id
    return item_id


@app.get("/items/{item_id}")
def read_item(item_id: str):
    # Retrieve a document from Firestore with the specified ID
    doc_ref = db.collection("items").document(item_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        raise HTTPException(status_code=404, detail="Item not found")


@app.put("/items/{item_id}")
def update_item(item_id: str, item: Item):
    # Update a document in Firestore with the specified ID
    doc_ref = db.collection("items").document(item_id)
    doc = doc_ref.get()
    if doc.exists:
        item_dict = item.dict()
        item_dict["id"] = item_id
        doc_ref.set(item_dict)
        return item_dict
    else:
        raise HTTPException(status_code=404, detail="Item not found")


@app.delete("/items/{item_id}")
def delete_item(item_id: str):
    # Delete a document from Firestore with the specified ID
    doc_ref = db.collection("items").document(item_id)
    doc_ref.delete()
    return {"message": "Item deleted successfully"}


@app.get("/items")
async def list_items():
    collection_ref = db.collection('items')
    docs = collection_ref.stream()
    items = []
    for doc in docs:
        items.append(doc.to_dict())
    return {"items": items}


@app.get("/custom_metrics")
def metrics():
    red_metrics = RED_metrics.calculate_metrics()
    return {"requests_rate": red_metrics[0], "errors_count": red_metrics[1], "response_time_p95": red_metrics[2]}
