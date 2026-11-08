from fastapi import APIRouter

from ai_service.app.presentation.api.v1.endpoints.route_conversations import router as conversations_router
from app.presentation.api.v1.endpoints.route_chat import router as chat_router
from app.presentation.api.v1.endpoints.route_knowledge import router as knowledge_router

router = APIRouter()
router.include_router(conversations_router)
router.include_router(chat_router)
router.include_router(knowledge_router)
