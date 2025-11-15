from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.trends import get_country_search_density

app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Search endpoint
@app.get("/search")
def search_keyword(keyword: str):
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword is required")
    
    result = get_country_search_density(keyword)
    return {
        "keyword": keyword,
        "results": result
    }

# Test route
@app.get("/ping")
def ping():
    return {"message": "pong"}
