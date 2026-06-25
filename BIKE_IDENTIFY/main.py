from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# 1. Your Database (Expand this as you collect more data)
YEAR_MAP = {'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024, 'S': 2025, 'T': 2026}
EV_DATABASE = {
    "MAT62922": {
        "Make": "Tata", "Model": "Tigor EV", "Trim": "Standard",
        "Usable_Battery": "26 kWh", "Range": "315 km",
        "Warranty_Years": 8, "Warranty_KM": 160000
    }
}

# 2. Data Model for incoming requests
class VINRequest(BaseModel):
    vin: str

# 3. The API Endpoint
@app.post("/decode/")
async def decode_vin_endpoint(request: VINRequest):
    vin = request.vin.upper().strip()
    
    if len(vin) != 17:
        raise HTTPException(status_code=400, detail="VIN must be exactly 17 characters.")

    wmi = vin[0:3]
    vds = vin[3:8]
    year_char = vin[9]
    
    lookup_key = wmi + vds
    vehicle_data = EV_DATABASE.get(lookup_key)

    if not vehicle_data:
        raise HTTPException(status_code=404, detail="Vehicle specs not found in database.")

    # Return the data as a clean JSON object
    return {
        "Year": YEAR_MAP.get(year_char, "Unknown"),
        "Specs": vehicle_data
    }