from backend.routers.transitions import router as transitions_router
from backend.routers.documents import router as documents_router
from backend.routers.profile import router as profile_router
from backend.routers.knowledge import router as knowledge_router
from backend.routers.kt_levels import router as kt_levels_router
from backend.routers.stakeholders import router as stakeholders_router
from backend.routers.availability import router as availability_router
from backend.routers.scheduling import router as scheduling_router
from backend.routers.governance import router as governance_router
from backend.routers.export import router as export_router
from backend.routers.database_gateway import router as database_gateway_router
from backend.routers.modules import router as modules_router

__all__ = [
    "transitions_router",
    "documents_router",
    "profile_router",
    "knowledge_router",
    "kt_levels_router",
    "stakeholders_router",
    "availability_router",
    "scheduling_router",
    "governance_router",
    "export_router",
    "database_gateway_router",
    "modules_router",
]

