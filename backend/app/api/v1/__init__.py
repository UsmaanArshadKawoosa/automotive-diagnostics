from fastapi import APIRouter

from app.api.v1.diagnostics import router as diagnostics_router
from app.api.v1.knowledge import router as knowledge_router

router = APIRouter(prefix="/v1")
router.include_router(diagnostics_router)
router.include_router(knowledge_router)
