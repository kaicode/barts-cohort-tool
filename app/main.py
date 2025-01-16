from fastapi import FastAPI
from app.routes import snomed_route

app = FastAPI()

app.include_router(snomed_route.router)

@app.get("/")
async def root():
    return {"message": "API root"}
