from fastapi import FastAPI

from routers import router

app = FastAPI(
    title="Telecom Analytics API"
)

app.include_router(
    router
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)