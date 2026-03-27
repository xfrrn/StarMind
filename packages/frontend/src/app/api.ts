/**
 * StarMind API client — communicates with the Python backend.
 */

import type { Repository } from './data';

// Development: use Vite proxy (/api -> backend via vite.config.ts)
// Production: use full URL from environment variable
const API_BASE = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api`
  : '/api';

// Cache configuration
const MAX_CACHE_SIZE = 100;
const inflightGetRequests = new Map<string, Promise<unknown>>();
const getResponseCache = new Map<string, { expiresAt: number; data: unknown }>();

// Cache key generation for consistent hashing
function generateCacheKey(url: string): string {
    return url;
}

// Evict oldest entries when cache is full
function evictIfNeeded(): void {
    if (getResponseCache.size >= MAX_CACHE_SIZE) {
        // Remove oldest 20% of entries
        const entriesToRemove = Math.floor(MAX_CACHE_SIZE * 0.2);
        const entries = Array.from(getResponseCache.entries());
        // Sort by expiresAt and remove oldest
        entries.sort((a, b) => a[1].expiresAt - b[1].expiresAt);
        for (let i = 0; i < entriesToRemove; i++) {
            getResponseCache.delete(entries[i][0]);
        }
    }
}

// Clear cache for specific patterns or entire cache
export function clearApiCache(pattern?: string): void {
    if (!pattern) {
        getResponseCache.clear();
        return;
    }
    // Clear entries matching pattern
    for (const key of getResponseCache.keys()) {
        if (key.includes(pattern)) {
            getResponseCache.delete(key);
        }
    }
}

async function fetchJsonGet<T>(url: string, cacheTtlMs = 0): Promise<T> {
    const cacheKey = generateCacheKey(url);
    const now = Date.now();

    // Check cache
    const cached = getResponseCache.get(cacheKey);
    if (cached && cached.expiresAt > now) {
        return cached.data as T;
    }

    // Deduplicate in-flight requests
    const inflight = inflightGetRequests.get(cacheKey);
    if (inflight) {
        return inflight as Promise<T>;
    }

    const request = (async () => {
        const resp = await fetch(url);
        if (!resp.ok) {
            throw new Error(`Request failed: ${resp.status} ${resp.statusText}`);
        }
        const data = (await resp.json()) as T;
        if (cacheTtlMs > 0) {
            evictIfNeeded();
            getResponseCache.set(cacheKey, { expiresAt: now + cacheTtlMs, data });
        }
        return data;
    })();

    inflightGetRequests.set(cacheKey, request);
    try {
        return await request;
    } finally {
        inflightGetRequests.delete(cacheKey);
    }
}

// ---- Chat ----

export interface ChatResponse {
    answer: string;
    repositories: Repository[];
}

export async function chatSearch(query: string): Promise<ChatResponse> {
    const resp = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
    });
    if (!resp.ok) throw new Error(`Chat failed: ${resp.statusText}`);
    return resp.json();
}

export interface StatusEvent {
    stage: string;
    message: string;
}

export interface StreamCallbacks {
    onStatus?: (status: StatusEvent) => void;
    onRepositories: (repos: Repository[]) => void;
    onToken: (token: string) => void;
    onDone: () => void;
    onError: (error: string) => void;
}

export function chatSearchStream(query: string, callbacks: StreamCallbacks): () => void {
    const controller = new AbortController();

    (async () => {
        try {
            const resp = await fetch(`${API_BASE}/chat/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query }),
                signal: controller.signal,
            });

            if (!resp.ok) {
                callbacks.onError(`Chat failed: ${resp.statusText}`);
                return;
            }

            const reader = resp.body?.getReader();
            if (!reader) {
                callbacks.onError('No response body');
                return;
            }

            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                let eventType = '';
                for (const line of lines) {
                    if (line.startsWith('event:')) {
                        eventType = line.slice(6).trim();
                    } else if (line.startsWith('data:')) {
                        const data = line.slice(5).trim();
                        if (eventType === 'status') {
                            try {
                                callbacks.onStatus?.(JSON.parse(data));
                            } catch {
                                /* ignore parse errors */
                            }
                        } else if (eventType === 'repositories') {
                            try {
                                callbacks.onRepositories(JSON.parse(data));
                            } catch {
                                /* ignore parse errors */
                            }
                        } else if (eventType === 'token') {
                            // Unescape newlines
                            callbacks.onToken(data.replace(/\\n/g, '\n'));
                        } else if (eventType === 'done') {
                            callbacks.onDone();
                        } else if (eventType === 'error') {
                            callbacks.onError(data);
                        }
                    }
                }
            }
        } catch (err: any) {
            if (err.name !== 'AbortError') {
                callbacks.onError(err.message || 'Stream failed');
            }
        }
    })();

    return () => controller.abort();
}

// ---- Conversations ----

export interface Conversation {
    id: string;
    title: string;
    createdAt: string | null;
    updatedAt: string | null;
    messageCount: number;
    lastMessage: string;
}

export interface Message {
    id: number;
    conversationId: string;
    role: string;
    content: string;
    createdAt: string | null;
}

export interface ConversationDetail extends Conversation {
    messages: Message[];
}

export async function listConversations(limit = 20, offset = 0): Promise<Conversation[]> {
    const resp = await fetch(`${API_BASE}/conversations?limit=${limit}&offset=${offset}`);
    if (!resp.ok) throw new Error(`Failed to list conversations: ${resp.statusText}`);
    return resp.json();
}

export async function createConversation(title = ''): Promise<Conversation> {
    const resp = await fetch(`${API_BASE}/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
    });
    if (!resp.ok) throw new Error(`Failed to create conversation: ${resp.statusText}`);
    return resp.json();
}

export async function getConversation(id: string): Promise<ConversationDetail> {
    const resp = await fetch(`${API_BASE}/conversations/${id}`);
    if (!resp.ok) throw new Error(`Failed to get conversation: ${resp.statusText}`);
    return resp.json();
}

export async function deleteConversation(id: string): Promise<void> {
    const resp = await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' });
    if (!resp.ok) throw new Error(`Failed to delete conversation: ${resp.statusText}`);
}

export async function addMessage(conversationId: string, role: string, content: string): Promise<Message> {
    const resp = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, content }),
    });
    if (!resp.ok) throw new Error(`Failed to add message: ${resp.statusText}`);
    return resp.json();
}

// ---- Repositories ----

export interface RepoListResponse {
    repositories: Repository[];
    total: number;
    page: number;
    limit: number;
}

export interface RepoFilters {
    search?: string;
    language?: string;
    category?: string;
    has_ui?: boolean;
    has_api?: boolean;
    activity_level?: string;
    stars_min?: number;
    stars_max?: number;
    sort_by?: 'stars' | 'stars_asc' | 'name' | 'updated';
    page?: number;
    limit?: number;
}

// Default cache TTLs for different data types
const CACHE_TTL = {
    stats: 30_000,      // 30 seconds - stats change rarely
    repository: 60_000, // 60 seconds - repo details are stable
    repos: 0,           // No caching for list - filters change frequently
};

export async function fetchRepositories(filters: RepoFilters = {}): Promise<RepoListResponse> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            params.set(key, String(value));
        }
    });
    return fetchJsonGet<RepoListResponse>(`${API_BASE}/repositories?${params}`, CACHE_TTL.repos);
}

export async function fetchRepository(id: string): Promise<Repository> {
    return fetchJsonGet<Repository>(`${API_BASE}/repositories/${id}`, CACHE_TTL.repository);
}

// ---- Stats ----

export interface StatsResponse {
    total: number;
    languages: Record<string, number>;
    categories: Record<string, number>;
}

export async function fetchStats(): Promise<StatsResponse> {
    return fetchJsonGet<StatsResponse>(`${API_BASE}/stats`, CACHE_TTL.stats);
}

// ---- Sync ----

export interface SyncStatusResponse {
    is_syncing: boolean;
    progress: number;
    total: number;
    current_repo: string;
    total_stars: number;
    indexed_repos: number;
    pending_repos: number;
    last_sync: string | null;
    logs: Array<{ status: string; time: string; details: string }>;
}

export interface SyncTriggerResponse {
    message: string;
    status: string;
}

export const triggerSync = async (fullSync = false): Promise<SyncTriggerResponse> => {
    const url = fullSync ? `${API_BASE}/sync?full_sync=true` : `${API_BASE}/sync`;
    const response = await fetch(url, {
        method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to trigger sync');
    return response.json();
};

export const triggerAiAnalysis = async (): Promise<SyncTriggerResponse> => {
    const response = await fetch(`${API_BASE}/sync/analyze`, {
        method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to trigger AI analysis');
    return response.json();
};

export const getSyncStatus = async (): Promise<SyncStatusResponse> => {
    const response = await fetch(`${API_BASE}/sync/status`);
    if (!response.ok) throw new Error('Failed to get sync status');
    return response.json();
};

// ---- Settings ----

export interface SettingsData {
    // User Info
    github_username: string;
    first_name: string;
    last_name: string;
    email: string;
    // API Keys (masked)
    github_token_set: boolean;
    github_token_masked: string;
    openai_api_key_set: boolean;
    openai_api_key_masked: string;
    openai_base_url: string;
    openai_model: string;
    // Chat Retrieval
    chat_similarity_threshold: number;
    chat_llm_filter_enabled: boolean;
    // Sync Configuration
    github_sync_page_concurrency: number;
    github_readme_concurrency: number;
    ai_analysis_concurrency: number;
    // Feature Toggles
    auto_summarize: boolean;
    include_readmes: boolean;
    // Auto Sync
    auto_sync_enabled: boolean;
    auto_sync_time: string;
    timezone: string;
    last_sync_at: string | null;
}

export interface SettingsUpdate {
    github_username?: string;
    first_name?: string;
    last_name?: string;
    email?: string;
    github_token?: string;
    openai_api_key?: string;
    openai_base_url?: string;
    openai_model?: string;
    chat_similarity_threshold?: number;
    chat_llm_filter_enabled?: boolean;
    github_sync_page_concurrency?: number;
    github_readme_concurrency?: number;
    ai_analysis_concurrency?: number;
    auto_summarize?: boolean;
    include_readmes?: boolean;
    auto_sync_enabled?: boolean;
    auto_sync_time?: string;
    timezone?: string;
}

export interface TestConnectionResponse {
    success: boolean;
    message: string;
}

export async function fetchSettings(): Promise<SettingsData> {
    const resp = await fetch(`${API_BASE}/settings`);
    if (!resp.ok) throw new Error(`Fetch settings failed: ${resp.statusText}`);
    return resp.json();
}

export async function updateSettings(data: SettingsUpdate): Promise<SettingsData> {
    const resp = await fetch(`${API_BASE}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`Update settings failed: ${resp.statusText}`);
    return resp.json();
}

export async function testGithubConnection(): Promise<TestConnectionResponse> {
    const resp = await fetch(`${API_BASE}/settings/test-github`, {
        method: 'POST',
    });
    if (!resp.ok) throw new Error(`Test GitHub failed: ${resp.statusText}`);
    return resp.json();
}

export async function testOpenaiConnection(): Promise<TestConnectionResponse> {
    const resp = await fetch(`${API_BASE}/settings/test-openai`, {
        method: 'POST',
    });
    if (!resp.ok) throw new Error(`Test OpenAI failed: ${resp.statusText}`);
    return resp.json();
}

// ---- Repo Chat ----

export interface RepoChatTurn {
    role: 'user' | 'assistant';
    message: string;
}

export interface RepoChatResponse {
    answer: string;
    repo: Repository;
}

export async function chatWithRepo(
    repoId: string,
    message: string,
    history: RepoChatTurn[] = []
): Promise<RepoChatResponse> {
    const resp = await fetch(`${API_BASE}/chat/repo/${repoId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history }),
    });
    if (!resp.ok) throw new Error(`Chat failed: ${resp.statusText}`);
    return resp.json();
}


// ---- Collections ----

export interface Collection {
    id: string;
    name: string;
    description: string;
    tags: string[];
    color: string;
    icon: string;
    repo_count: number;
    created_at?: string;
    updated_at?: string;
}

export interface CollectionCreate {
    name: string;
    description?: string;
    tags?: string[];
    color?: string;
    icon?: string;
}

export interface CollectionUpdate {
    name?: string;
    description?: string;
    tags?: string[];
    color?: string;
    icon?: string;
}

export interface CollectionRepo {
    id: string;
    name: string;
    description: string;
    language: string;
    stars: number;
    tags: string[];
    category: string;
    url: string;
    notes: string;
}

export interface CollectionReposResponse {
    repositories: CollectionRepo[];
    total: number;
    page: number;
    limit: number;
    has_more: boolean;
}

export async function listCollections(includeRepos = false): Promise<Collection[]> {
    const url = `${API_BASE}/collections?include_repos=${includeRepos}`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`Fetch collections failed: ${resp.statusText}`);
    const data = await resp.json();
    return data.collections;
}

export async function getCollection(collectionId: string): Promise<Collection> {
    const resp = await fetch(`${API_BASE}/collections/${collectionId}`);
    if (!resp.ok) throw new Error(`Fetch collection failed: ${resp.statusText}`);
    return resp.json();
}

export async function createCollection(data: CollectionCreate): Promise<Collection> {
    const resp = await fetch(`${API_BASE}/collections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`Create collection failed: ${resp.statusText}`);
    return resp.json();
}

export async function updateCollection(collectionId: string, data: CollectionUpdate): Promise<Collection> {
    const resp = await fetch(`${API_BASE}/collections/${collectionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`Update collection failed: ${resp.statusText}`);
    return resp.json();
}

export async function deleteCollection(collectionId: string): Promise<void> {
    const resp = await fetch(`${API_BASE}/collections/${collectionId}`, {
        method: 'DELETE',
    });
    if (!resp.ok) throw new Error(`Delete collection failed: ${resp.statusText}`);
}

export async function addRepoToCollection(
    collectionId: string,
    repoId: number,
    notes = ""
): Promise<void> {
    const resp = await fetch(`${API_BASE}/collections/${collectionId}/repos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_id: repoId, notes }),
    });
    if (!resp.ok) throw new Error(`Add repo to collection failed: ${resp.statusText}`);
}

export async function removeRepoFromCollection(
    collectionId: string,
    repoId: number
): Promise<void> {
    const resp = await fetch(`${API_BASE}/collections/${collectionId}/repos/${repoId}`, {
        method: 'DELETE',
    });
    if (!resp.ok) throw new Error(`Remove repo from collection failed: ${resp.statusText}`);
}

export async function getCollectionRepos(
    collectionId: string,
    page = 1,
    limit = 20
): Promise<CollectionReposResponse> {
    const resp = await fetch(`${API_BASE}/collections/${collectionId}/repos?page=${page}&limit=${limit}`);
    if (!resp.ok) throw new Error(`Fetch collection repos failed: ${resp.statusText}`);
    return resp.json();
}

export async function getRepoCollections(repoId: number): Promise<Collection[]> {
    const resp = await fetch(`${API_BASE}/repositories/${repoId}/collections`);
    if (!resp.ok) throw new Error(`Fetch repo collections failed: ${resp.statusText}`);
    const data = await resp.json();
    return data.collections;
}

export async function getAllCollectionTags(): Promise<string[]> {
    const resp = await fetch(`${API_BASE}/collections/tags`);
    if (!resp.ok) throw new Error(`Fetch tags failed: ${resp.statusText}`);
    const data = await resp.json();
    return data.tags;
}


// ---- Repo Notes ----

export interface NoteResponse {
    note: string;
}

export async function getRepoNote(repoId: string): Promise<NoteResponse> {
    const resp = await fetch(`${API_BASE}/repositories/${repoId}/note`);
    if (!resp.ok) throw new Error(`Fetch note failed: ${resp.statusText}`);
    return resp.json();
}

export async function updateRepoNote(repoId: string, note: string): Promise<NoteResponse> {
    const resp = await fetch(`${API_BASE}/repositories/${repoId}/note`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note }),
    });
    if (!resp.ok) throw new Error(`Update note failed: ${resp.statusText}`);
    return resp.json();
}

export async function deleteRepoNote(repoId: string): Promise<void> {
    const resp = await fetch(`${API_BASE}/repositories/${repoId}/note`, {
        method: 'DELETE',
    });
    if (!resp.ok) throw new Error(`Delete note failed: ${resp.statusText}`);
}


// ---- Dashboard ----

export interface DistributionItem {
    name: string;
    count: number;
}

export interface DashboardResponse {
    total_repos: number;
    total_collections: number;
    languages: DistributionItem[];
    categories: DistributionItem[];
    activity_levels: DistributionItem[];
    stars_distribution: DistributionItem[];
}

export async function fetchDashboard(): Promise<DashboardResponse> {
    return fetchJsonGet<DashboardResponse>(`${API_BASE}/dashboard`, CACHE_TTL.stats);
}


// ---- Share ----

export interface ShareStatusResponse {
    is_shared: boolean;
    share_id: string | null;
    share_url: string | null;
    view_count: number;
}

export interface ShareResponse {
    share_id: string;
    share_url: string;
}

export async function getShareStatus(collectionId: string): Promise<ShareStatusResponse> {
    const resp = await fetch(`${API_BASE}/collections/${collectionId}/share`);
    if (!resp.ok) throw new Error(`Fetch share status failed: ${resp.statusText}`);
    return resp.json();
}

export async function createShare(collectionId: string): Promise<ShareResponse> {
    const resp = await fetch(`${API_BASE}/collections/${collectionId}/share`, {
        method: 'POST',
    });
    if (!resp.ok) throw new Error(`Create share failed: ${resp.statusText}`);
    return resp.json();
}

export async function deleteShare(collectionId: string): Promise<void> {
    const resp = await fetch(`${API_BASE}/collections/${collectionId}/share`, {
        method: 'DELETE',
    });
    if (!resp.ok) throw new Error(`Delete share failed: ${resp.statusText}`);
}


// ---- Public Shared ----

export interface PublicCollectionRepo {
    id: number;
    name: string;
    description: string;
    language: string;
    stars: number;
    url: string;
    notes: string;
}

export interface PublicCollectionResponse {
    name: string;
    description: string;
    tags: string[];
    color: string;
    icon: string;
    repo_count: number;
    repositories: PublicCollectionRepo[];
}

export async function getPublicSharedCollection(shareId: string): Promise<PublicCollectionResponse> {
    const resp = await fetch(`${API_BASE}/public/shared/${shareId}`);
    if (!resp.ok) throw new Error(`Fetch shared collection failed: ${resp.statusText}`);
    return resp.json();
}


// ---- Backup ----

export interface ImportStats {
    collections: number;
    notes: number;
    repos_added: number;
}

export interface ImportResponse {
    message: string;
    stats: ImportStats;
}

export function getBackupExportUrl(): string {
    return `${API_BASE}/backup/export`;
}

export async function importBackup(file: File): Promise<ImportResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const resp = await fetch(`${API_BASE}/backup/import`, {
        method: 'POST',
        body: formData,
    });
    if (!resp.ok) {
        const error = await resp.json().catch(() => ({ detail: 'Import failed' }));
        throw new Error(error.detail || 'Import failed');
    }
    return resp.json();
}


// ---- Archives ----

export interface ArchiveStatus {
    is_archived: boolean;
    archive_path: string;
    archive_size: number;
    archive_sha: string;
    archived_at: string | null;
}

export interface ArchivedRepo {
    id: number;
    name: string;
    description: string;
    language: string;
    stars: number;
    archive_size: number;
    archived_at: string | null;
}

export async function getArchiveStatus(repoId: string): Promise<ArchiveStatus> {
    const resp = await fetch(`${API_BASE}/repositories/${repoId}/archive`);
    if (!resp.ok) throw new Error(`Fetch archive status failed: ${resp.statusText}`);
    return resp.json();
}

export async function createArchive(repoId: string): Promise<ArchiveStatus> {
    const resp = await fetch(`${API_BASE}/repositories/${repoId}/archive`, {
        method: 'POST',
    });
    if (!resp.ok) throw new Error(`Create archive failed: ${resp.statusText}`);
    return resp.json();
}

export async function deleteArchive(repoId: string): Promise<void> {
    const resp = await fetch(`${API_BASE}/repositories/${repoId}/archive`, {
        method: 'DELETE',
    });
    if (!resp.ok) throw new Error(`Delete archive failed: ${resp.statusText}`);
}

export function getArchiveDownloadUrl(repoId: string): string {
    return `${API_BASE}/repositories/${repoId}/archive/download`;
}

export async function listArchives(): Promise<{ repositories: ArchivedRepo[]; total: number }> {
    const resp = await fetch(`${API_BASE}/archives`);
    if (!resp.ok) throw new Error(`Fetch archives failed: ${resp.statusText}`);
    return resp.json();
}


// ---- Archive Share ----

export interface ArchiveShareStatus {
    is_shared: boolean;
    share_id: string | null;
    share_url: string | null;
    expires_at: string | null;
    view_count: number;
}

export interface ArchiveShareCreate {
    share_id: string;
    share_url: string;
    expires_at: string;
}

export interface SharedArchiveInfo {
    repo_name: string;
    repo_description: string;
    archive_size: number;
    expires_at: string;
    view_count: number;
}

export async function getArchiveShareStatus(repoId: string): Promise<ArchiveShareStatus> {
    const resp = await fetch(`${API_BASE}/repositories/${repoId}/share`);
    if (!resp.ok) throw new Error(`Fetch share status failed: ${resp.statusText}`);
    return resp.json();
}

export async function createArchiveShare(repoId: string, expiresInHours: number): Promise<ArchiveShareCreate> {
    const resp = await fetch(`${API_BASE}/repositories/${repoId}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expires_in_hours: expiresInHours }),
    });
    if (!resp.ok) throw new Error(`Create share failed: ${resp.statusText}`);
    return resp.json();
}

export async function deleteArchiveShare(repoId: string): Promise<void> {
    const resp = await fetch(`${API_BASE}/repositories/${repoId}/share`, {
        method: 'DELETE',
    });
    if (!resp.ok) throw new Error(`Delete share failed: ${resp.statusText}`);
}

export async function getSharedArchiveInfo(shareId: string): Promise<SharedArchiveInfo> {
    const resp = await fetch(`${API_BASE}/public/archive/${shareId}`);
    if (!resp.ok) throw new Error(`Fetch shared archive failed: ${resp.statusText}`);
    return resp.json();
}

export function getSharedArchiveDownloadUrl(shareId: string): string {
    return `${API_BASE}/public/archive/${shareId}/download`;
}
