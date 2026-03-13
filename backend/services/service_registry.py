"""Service object registry (application-level singletons)."""

from config import get_settings
from core.analysis import ChatResponder, RepositoryAnalyzer
from core.llm import LLMClient
from core.retrieval import EmbeddingService, RepositorySearchService
from services.analysis_service import AnalysisService
from services.chat_service import ChatService
from services.readme_cleaner import ReadmeCleaner
from services.repository_service import RepositoryService
from services.settings_service import SettingsService
from services.sync_runtime_state import SyncRuntimeState
from services.sync_service import SyncService

settings = get_settings()

llm_client = LLMClient(settings)
embedding_service = EmbeddingService(settings, llm_client)
search_service = RepositorySearchService(settings, embedding_service)
repository_analyzer = RepositoryAnalyzer(settings, llm_client)
chat_responder = ChatResponder(llm_client)
runtime_state = SyncRuntimeState()
readme_cleaner = ReadmeCleaner()

analysis_service = AnalysisService(
    settings=settings,
    runtime_state=runtime_state,
    repository_analyzer=repository_analyzer,
    embedding_service=embedding_service,
    readme_cleaner=readme_cleaner,
)
sync_service = SyncService(
    settings=settings,
    runtime_state=runtime_state,
    analysis_service=analysis_service,
)
chat_service = ChatService(search_service=search_service, chat_responder=chat_responder)
repository_service = RepositoryService(settings)
settings_service = SettingsService()


def get_chat_service() -> ChatService:
    return chat_service


def get_repository_service() -> RepositoryService:
    return repository_service


def get_settings_service() -> SettingsService:
    return settings_service


def get_analysis_service() -> AnalysisService:
    return analysis_service


def get_sync_service() -> SyncService:
    return sync_service
