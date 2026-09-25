from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.formulas import router as formulas_router
from .routes.posts import router as posts_router

app = FastAPI(title="Formula Descriptors Viewer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts_router, prefix="/api")
app.include_router(formulas_router, prefix="/api")
