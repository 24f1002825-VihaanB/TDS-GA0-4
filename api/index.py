from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os

# 1. Set up the FastAPI App
app = FastAPI()

# 2. Enable CORS (Allows the dashboard to talk to your bot)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False, # <-- FIXED: This must be False when using "*"
    allow_methods=["*"],     # <-- FIXED: Changed to "*" so OPTIONS preflight requests pass
    allow_headers=["*"],
)

# 3. Define the incoming request body
class AnalyticsRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

# 4. Load your JSON data safely
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT_DIR, "q-vercel-latency.json")

with open(JSON_PATH, "r") as f:
    telemetry_data = json.load(f)

# Helper function to calculate the 95th percentile
def get_p95(data_list):
    if not data_list:
        return 0
    sorted_data = sorted(data_list)
    index = int(0.95 * len(sorted_data))
    return sorted_data[index]

# 5. Create the POST endpoint
@app.post("/")
def calculate_metrics(request: AnalyticsRequest):
    results = {}
    
    # Loop through each region requested (e.g., "amer", "emea")
    for region in request.regions:
        
        # Filter the telemetry data down to JUST this region
        region_records = [item for item in telemetry_data if item.get("region") == region]
        
        if not region_records:
            continue
            
        # Extract just the numbers we need, using the EXACT keys from your file
        latencies = [item["latency_ms"] for item in region_records]
        uptimes = [item["uptime_pct"] for item in region_records] # FIXED: Now looks for "uptime_pct"
        
        # Calculate the math
        avg_latency = sum(latencies) / len(latencies)
        avg_uptime = sum(uptimes) / len(uptimes)
        p95_latency = get_p95(latencies)
        
        # Count how many records broke the threshold
        breaches = sum(1 for lat in latencies if lat > request.threshold_ms)
        
        # Save this region's answers into our final result
        results[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,  
            "breaches": breaches
        }
        
    return results
