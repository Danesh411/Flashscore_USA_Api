from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime, timezone

import time
from main import main  # import main from main.py
from pymongo import MongoClient

def log_to_mongodb(log):
    required_fields = {
        "endpoint": str,
        "request_url": str,
        "status_code": int,
        "request_time": datetime,
        "elapsed": (int, float),
        "params": dict,
        "payload": dict,
        "data": dict,
        "response_path": str
    }

    for field, field_type in required_fields.items():
        if field not in log or not isinstance(log[field], field_type):
            raise ValueError(f"Missing or invalid field: {field}")

    optional_fields = {
        "error_message": (str, type(None)),
        "proxy": (str, type(None)),
        "cost": str
    }

    for field, field_type in optional_fields.items():
        if field in log and not isinstance(log[field], field_type):
            raise ValueError(f"Invalid type for optional field: {field}")

    try:
        client = MongoClient("")
        db = client["flashscoreusa_api"]
        collection = db["logs"]
        result = collection.insert_one(log)
        print(f"Log inserted with ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        print(f"Error inserting log into MongoDB: {e}")
        return None


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

VALID_API_KEYS = ["K59328410M", "K59328410MTT"]
VALID_PLATFORMS = ['baseball', 'football', 'basketball', 'soccer']

@app.get("/flashscore/data")
async def get_data(
    platform: str = Query(..., description="Choose from baseball, football, baseketball, soccer"),
    apikey: str = Query(..., description="Your API key")
):
    start_time = time.time()
    log_base = {
        "endpoint": "http://51.222.244.92:1278/flashscore/data",
        "request_url": f"/flashscore/data?platform={platform}&apikey={apikey}",
        "request_time": datetime.now(timezone.utc),
        "elapsed": 0,
        "params": {"platform": platform, "key": apikey},
        "payload": {},
        "data": {},
        "response_path": "",
        "error_message": None,
    }
    # Validate API key
    if apikey not in VALID_API_KEYS:
        log_base["status_code"] = 401
        log_base["elapsed"] = time.time() - start_time
        log_base["error_message"] = "Invalid API Key"
        log_to_mongodb(log_base)
        return JSONResponse(status_code=401, content={"status": 401, "message": "Invalid API Key"})

    # Validate platform
    if platform.lower() not in VALID_PLATFORMS:
        log_base["status_code"] = 400
        log_base["elapsed"] = time.time() - start_time
        log_base["error_message"] = "Invalid platform"
        log_to_mongodb(log_base)
        return JSONResponse(status_code=400, content={"status": 400, "message": "Invalid platform"})

    try:
        result = main(platform)  # Call the appropriate extraction
        if result == "No matches Available":
            log_base["status_code"] = 404
            log_base["elapsed"] = time.time() - start_time
            log_base["error_message"] = "No matches Available"
            log_to_mongodb(log_base)
            return JSONResponse(status_code=404, content={"status": 404, "platform": platform, "data": result})
        log_base["status_code"] = 200
        log_base["elapsed"] = time.time() - start_time
        log_to_mongodb(log_base)
        return JSONResponse(status_code=200, content={"status": 200, "platform": platform, "data": result})
    except Exception as e:
        log_base["status_code"] = 500
        log_base["error_message"] = str(e)
        log_base["elapsed"] = time.time() - start_time
        log_to_mongodb(log_base)
        return JSONResponse(status_code=500, content={"status": 500, "message": f"Server Error: {str(e)}"})

@app.get("/")
async def root():
    return JSONResponse(content={"status": 200, "message": "API is running!"})

if __name__ == "__main__":
    uvicorn.run("lambda:app", host="51.222.244.92", port=1278, reload=True)
