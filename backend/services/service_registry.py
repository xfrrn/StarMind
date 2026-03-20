"""Service object registry (application-level singletons)."""

from config import get_settings
from core.analysis import RepositoryAnalyzer
from core.llm import LLMClient
from core.retrieval import EmbeddingService, RepositorySearchService
from services.application import (
    AnalysisService,
    RepositoryService,
    SettingsService,
    SyncService,
)
from services.application.runtime import SyncRuntimeState
from services.chat.chat_service import ChatService
from services.domain import StateTransitionService
from services.readme_cleaning.cleaner import ReadmeCleaner

settings = get_settings()

llm_client = LLMClient(settings)
embedding_service = EmbeddingService(settings, llm_client)
search_service = RepositorySearchService(settings, embedding_service)
repository_analyzer = RepositoryAnalyzer(settings, llm_client)
runtime_state = SyncRuntimeState()
readme_cleaner = ReadmeCleaner()
state_transition_service = StateTransitionService()

analysis_service = AnalysisService(
    settings=settings,
    runtime_state=runtime_state,
    repository_analyzer=repository_analyzer,
    embedding_service=embedding_service,
    readme_cleaner=readme_cleaner,
    state_transition_service=state_transition_service,
)
sync_service = SyncService(
    settings=settings,
    runtime_state=runtime_state,
    analysis_service=analysis_service,
    readme_cleaner=readme_cleaner,
    state_transition_service=state_transition_service,
)
chat_service = ChatService(
    settings=settings,
    llm_client=llm_client,
    embedding_service=embedding_service,
)
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
