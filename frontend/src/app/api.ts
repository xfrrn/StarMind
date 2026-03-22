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

export const triggerSync = async (): Promise<SyncTriggerResponse> => {
    const response = await fetch(`${API_BASE}/sync`, {
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
    github_username: string;
    auto_summarize: boolean;
    include_readmes: boolean;
    first_name: string;
    last_name: string;
    email: string;
}

export async function fetchSettings(): Promise<SettingsData> {
    const resp = await fetch(`${API_BASE}/settings`);
    if (!resp.ok) throw new Error(`Fetch settings failed: ${resp.statusText}`);
    return resp.json();
}

export async function updateSettings(data: Partial<SettingsData>): Promise<SettingsData> {
    const resp = await fetch(`${API_BASE}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`Update settings failed: ${resp.statusText}`);
    return resp.json();
}
