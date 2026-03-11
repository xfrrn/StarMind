/**
 * StarMind API client — communicates with the Python backend.
 */

import type { Repository } from './data';

const API_BASE = '/api';

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

export async function fetchRepositories(filters: RepoFilters = {}): Promise<RepoListResponse> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            params.set(key, String(value));
        }
    });
    const resp = await fetch(`${API_BASE}/repositories?${params}`);
    if (!resp.ok) throw new Error(`Fetch repos failed: ${resp.statusText}`);
    return resp.json();
}

export async function fetchRepository(id: string): Promise<Repository> {
    const resp = await fetch(`${API_BASE}/repositories/${id}`);
    if (!resp.ok) throw new Error(`Fetch repo failed: ${resp.statusText}`);
    return resp.json();
}

// ---- Stats ----

export interface StatsResponse {
    total: number;
    languages: Record<string, number>;
    categories: Record<string, number>;
}

export async function fetchStats(): Promise<StatsResponse> {
    const resp = await fetch(`${API_BASE}/stats`);
    if (!resp.ok) throw new Error(`Fetch stats failed: ${resp.statusText}`);
    return resp.json();
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
