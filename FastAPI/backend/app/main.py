from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.upload_router import router as upload_router_router

app = FastAPI(
    title="Jeonse Fraud Prevention API",
    description="전세계약서 업로드 및 분석을 위한 백엔드 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    upload_router_router,
    prefix="/api",
    tags=["upload"],
)


@app.get("/")
async def root():
    return {"message": "Jeonse Fraud Prevention API is running"}