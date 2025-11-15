from typing import Union
#import username search function
from fastapi import FastAPI
from routers.maigret_router import router as maigret_router


app = FastAPI()
app.include_router(maigret_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}