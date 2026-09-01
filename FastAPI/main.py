from fastapi import FastAPI

from routers import router

app = FastAPI(
    title="Telecom Analytics API"
)

app.include_router(
    router
)