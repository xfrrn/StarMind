import React, { useState, useEffect } from 'react';
import {
  User,
  Key,
  Sparkles,
  RefreshCw,
  Palette,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
  Loader2,
} from 'lucide-react';
import {
  fetchSettings,
  updateSettings,
  testGithubConnection,
  testOpenaiConnection,
  type SettingsData,
  type SettingsUpdate,
} from '../api';
import { useTheme, type Theme } from '../hooks/useTheme';

type TabId = 'account' | 'api-keys' | 'ai-config' | 'sync' | 'appearance';

const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'account', label: 'Account', icon: User },
  { id: 'api-keys', label: 'API Keys', icon: Key },
  { id: 'ai-config', label: 'AI Config', icon: Sparkles },
  { id: 'sync', label: 'Sync', icon: RefreshCw },
  { id: 'appearance', label: 'Appearance', icon: Palette },
];

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('account');
  const { theme, setTheme, resolvedTheme } = useTheme();

  // Form state
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [githubUsername, setGithubUsername] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [openaiApiKey, setOpenaiApiKey] = useState('');
  const [openaiBaseUrl, setOpenaiBaseUrl] = useState('');
  const [openaiModel, setOpenaiModel] = useState('');
  const [chatSimilarityThreshold, setChatSimilarityThreshold] = useState(0.5);
  const [chatLlmFilterEnabled, setChatLlmFilterEnabled] = useState(true);
  const [githubSyncPageConcurrency, setGithubSyncPageConcurrency] = useState(4);
  const [githubReadmeConcurrency, setGithubReadmeConcurrency] = useState(8);
  const [aiAnalysisConcurrency, setAiAnalysisConcurrency] = useState(1);
  const [autoSummarize, setAutoSummarize] = useState(true);
  const [includeReadmes, setIncludeReadmes] = useState(true);

  // UI state
  const [showGithubToken, setShowGithubToken] = useState(false);
  const [showOpenaiKey, setShowOpenaiKey] = useState(false);
  const [testingGithub, setTestingGithub] = useState(false);
  const [testingOpenai, setTestingOpenai] = useState(false);
  const [githubTestResult, setGithubTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [openaiTestResult, setOpenaiTestResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    fetchSettings()
      .then((data) => {
        setSettings(data);
        setFirstName(data.first_name);
        setLastName(data.last_name);
        setEmail(data.email);
        setGithubUsername(data.github_username);
        setOpenaiBaseUrl(data.openai_base_url);
        setOpenaiModel(data.openai_model);
        setChatSimilarityThreshold(data.chat_similarity_threshold);
        setChatLlmFilterEnabled(data.chat_llm_filter_enabled);
        setGithubSyncPageConcurrency(data.github_sync_page_concurrency);
        setGithubReadmeConcurrency(data.github_readme_concurrency);
        setAiAnalysisConcurrency(data.ai_analysis_concurrency);
        setAutoSummarize(data.auto_summarize);
        setIncludeReadmes(data.include_readmes);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleSave = async (updates: SettingsUpdate) => {
    setSaving(true);
    try {
      const updated = await updateSettings(updates);
      setSettings(updated);
      showMessage('success', 'Settings saved successfully.');
    } catch (err: any) {
      showMessage('error', `Error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleTestGithub = async () => {
    setTestingGithub(true);
    setGithubTestResult(null);
    try {
      const result = await testGithubConnection();
      setGithubTestResult(result);
    } catch (err: any) {
      setGithubTestResult({ success: false, message: err.message });
    } finally {
      setTestingGithub(false);
    }
  };

  const handleTestOpenai = async () => {
    setTestingOpenai(true);
    setOpenaiTestResult(null);
    try {
      const result = await testOpenaiConnection();
      setOpenaiTestResult(result);
    } catch (err: any) {
      setOpenaiTestResult({ success: false, message: err.message });
    } finally {
      setTestingOpenai(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin" />
      </div>
    );
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'account':
        return (
          <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
            <div className="px-6 py-5 border-b border-zinc-200 dark:border-zinc-800">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">Profile Information</h2>
            </div>
            <div className="p-6 space-y-6">
              <div className="flex items-center gap-6">
                <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-500 flex items-center justify-center text-white text-2xl font-bold shadow-md">
                  {firstName && lastName ? `${firstName[0]}${lastName[0]}` : 'SM'}
                </div>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">First Name</label>
                    <input
                      type="text"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Last Name</label>
                    <input
                      type="text"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Email Address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">GitHub Username</label>
                  <input
                    type="text"
                    value={githubUsername}
                    onChange={(e) => setGithubUsername(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
            <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end">
              <button
                onClick={() => handleSave({ first_name: firstName, last_name: lastName, email, github_username: githubUsername })}
                disabled={saving}
                className="px-5 py-2 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 rounded-xl font-medium transition-colors text-sm shadow-sm disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </section>
        );

      case 'api-keys':
        return (
          <div className="space-y-6">
            {/* GitHub Token */}
            <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
              <div className="px-6 py-5 border-b border-zinc-200 dark:border-zinc-800">
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">GitHub Token</h2>
                <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                  Required for syncing your starred repositories.
                </p>
              </div>
              <div className="p-6 space-y-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Personal Access Token</label>
                  <div className="relative">
                    <input
                      type={showGithubToken ? 'text' : 'password'}
                      value={githubToken}
                      onChange={(e) => setGithubToken(e.target.value)}
                      placeholder={settings?.github_token_set ? settings.github_token_masked : 'ghp_xxxxxxxxxxxx'}
                      className="w-full px-3 py-2 pr-20 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => setShowGithubToken(!showGithubToken)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
                    >
                      {showGithubToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {settings?.github_token_set && !githubToken && (
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">Token is set. Enter a new value to update.</p>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleTestGithub}
                    disabled={testingGithub || (!settings?.github_token_set && !githubToken)}
                    className="flex items-center gap-2 px-4 py-2 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-900 dark:text-zinc-50 rounded-lg font-medium transition-colors text-sm disabled:opacity-50"
                  >
                    {testingGithub ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Test Connection
                  </button>
                  {githubTestResult && (
                    <div className={`flex items-center gap-1.5 text-sm ${githubTestResult.success ? 'text-emerald-500' : 'text-red-500'}`}>
                      {githubTestResult.success ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                      {githubTestResult.message}
                    </div>
                  )}
                </div>
              </div>
              <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end">
                <button
                  onClick={() => githubToken && handleSave({ github_token: githubToken })}
                  disabled={saving || !githubToken}
                  className="px-5 py-2 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 rounded-xl font-medium transition-colors text-sm shadow-sm disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Token'}
                </button>
              </div>
            </section>

            {/* OpenAI API Key */}
            <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
              <div className="px-6 py-5 border-b border-zinc-200 dark:border-zinc-800">
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">OpenAI API Key</h2>
                <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                  Required for AI-powered features like chat and summaries.
                </p>
              </div>
              <div className="p-6 space-y-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">API Key</label>
                  <div className="relative">
                    <input
                      type={showOpenaiKey ? 'text' : 'password'}
                      value={openaiApiKey}
                      onChange={(e) => setOpenaiApiKey(e.target.value)}
                      placeholder={settings?.openai_api_key_set ? settings.openai_api_key_masked : 'sk-xxxxxxxxxxxx'}
                      className="w-full px-3 py-2 pr-20 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => setShowOpenaiKey(!showOpenaiKey)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
                    >
                      {showOpenaiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {settings?.openai_api_key_set && !openaiApiKey && (
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">Key is set. Enter a new value to update.</p>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleTestOpenai}
                    disabled={testingOpenai || (!settings?.openai_api_key_set && !openaiApiKey)}
                    className="flex items-center gap-2 px-4 py-2 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-900 dark:text-zinc-50 rounded-lg font-medium transition-colors text-sm disabled:opacity-50"
                  >
                    {testingOpenai ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Test Connection
                  </button>
                  {openaiTestResult && (
                    <div className={`flex items-center gap-1.5 text-sm ${openaiTestResult.success ? 'text-emerald-500' : 'text-red-500'}`}>
                      {openaiTestResult.success ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                      {openaiTestResult.message}
                    </div>
                  )}
                </div>
              </div>
              <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end">
                <button
                  onClick={() => openaiApiKey && handleSave({ openai_api_key: openaiApiKey })}
                  disabled={saving || !openaiApiKey}
                  className="px-5 py-2 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 rounded-xl font-medium transition-colors text-sm shadow-sm disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Key'}
                </button>
              </div>
            </section>
          </div>
        );

      case 'ai-config':
        return (
          <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
            <div className="px-6 py-5 border-b border-zinc-200 dark:border-zinc-800">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">AI Configuration</h2>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                Configure OpenAI settings and chat retrieval behavior.
              </p>
            </div>
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">OpenAI Base URL</label>
                  <input
                    type="text"
                    value={openaiBaseUrl}
                    onChange={(e) => setOpenaiBaseUrl(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">Change for Azure OpenAI or compatible APIs.</p>
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Model</label>
                  <input
                    type="text"
                    value={openaiModel}
                    onChange={(e) => setOpenaiModel(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">e.g., gpt-4o-mini, gpt-4o, gpt-3.5-turbo</p>
                </div>
              </div>

              <div className="border-t border-zinc-200 dark:border-zinc-800 pt-6">
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 mb-4">Chat Retrieval</h3>
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <div className="flex justify-between">
                      <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Similarity Threshold</label>
                      <span className="text-sm text-zinc-500 dark:text-zinc-400">{chatSimilarityThreshold.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={chatSimilarityThreshold}
                      onChange={(e) => setChatSimilarityThreshold(parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">Higher = stricter filtering. Results below this threshold are excluded.</p>
                  </div>

                  <label className="flex items-start gap-3 cursor-pointer">
                    <div className="pt-0.5">
                      <input
                        type="checkbox"
                        checked={chatLlmFilterEnabled}
                        onChange={(e) => setChatLlmFilterEnabled(e.target.checked)}
                        className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-700 text-blue-600 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <div className="font-medium text-sm text-zinc-900 dark:text-zinc-50">LLM Verification</div>
                      <div className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">Use LLM to verify each result is truly relevant after threshold filtering.</div>
                    </div>
                  </label>
                </div>
              </div>
            </div>
            <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end">
              <button
                onClick={() => handleSave({
                  openai_base_url: openaiBaseUrl,
                  openai_model: openaiModel,
                  chat_similarity_threshold: chatSimilarityThreshold,
                  chat_llm_filter_enabled: chatLlmFilterEnabled,
                })}
                disabled={saving}
                className="px-5 py-2 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 rounded-xl font-medium transition-colors text-sm shadow-sm disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </section>
        );

      case 'sync':
        return (
          <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
            <div className="px-6 py-5 border-b border-zinc-200 dark:border-zinc-800">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">Sync Configuration</h2>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                Control concurrency for GitHub sync and AI analysis.
              </p>
            </div>
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Page Concurrency</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={githubSyncPageConcurrency}
                    onChange={(e) => setGithubSyncPageConcurrency(parseInt(e.target.value) || 4)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">Concurrent page requests to GitHub API.</p>
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">README Concurrency</label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={githubReadmeConcurrency}
                    onChange={(e) => setGithubReadmeConcurrency(parseInt(e.target.value) || 8)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">Concurrent README fetches.</p>
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">AI Analysis Concurrency</label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={aiAnalysisConcurrency}
                    onChange={(e) => setAiAnalysisConcurrency(parseInt(e.target.value) || 1)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">Concurrent AI requests. Keep low to avoid rate limits.</p>
                </div>
              </div>

              <div className="border-t border-zinc-200 dark:border-zinc-800 pt-6">
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 mb-4">Feature Toggles</h3>
                <div className="space-y-4">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <div className="pt-0.5">
                      <input
                        type="checkbox"
                        checked={autoSummarize}
                        onChange={(e) => setAutoSummarize(e.target.checked)}
                        className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-700 text-blue-600 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <div className="font-medium text-sm text-zinc-900 dark:text-zinc-50">Auto-summarize new repositories</div>
                      <div className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">Automatically generate AI tags and summaries when syncing.</div>
                    </div>
                  </label>

                  <label className="flex items-start gap-3 cursor-pointer">
                    <div className="pt-0.5">
                      <input
                        type="checkbox"
                        checked={includeReadmes}
                        onChange={(e) => setIncludeReadmes(e.target.checked)}
                        className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-700 text-blue-600 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <div className="font-medium text-sm text-zinc-900 dark:text-zinc-50">Include READMEs in embeddings</div>
                      <div className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">Improves search quality but increases processing time.</div>
                    </div>
                  </label>
                </div>
              </div>
            </div>
            <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end">
              <button
                onClick={() => handleSave({
                  github_sync_page_concurrency: githubSyncPageConcurrency,
                  github_readme_concurrency: githubReadmeConcurrency,
                  ai_analysis_concurrency: aiAnalysisConcurrency,
                  auto_summarize: autoSummarize,
                  include_readmes: includeReadmes,
                })}
                disabled={saving}
                className="px-5 py-2 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 rounded-xl font-medium transition-colors text-sm shadow-sm disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </section>
        );

      case 'appearance':
        return (
          <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
            <div className="px-6 py-5 border-b border-zinc-200 dark:border-zinc-800">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">Appearance</h2>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                Customize how StarMind looks.
              </p>
            </div>
            <div className="p-6 space-y-6">
              <div className="space-y-3">
                <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Theme</label>
                <div className="grid grid-cols-3 gap-3">
                  {(['light', 'dark', 'system'] as Theme[]).map((t) => (
                    <button
                      key={t}
                      onClick={() => setTheme(t)}
                      className={`px-4 py-3 rounded-xl border text-sm font-medium transition-colors ${
                        theme === t
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400'
                          : 'border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 text-zinc-700 dark:text-zinc-300 hover:border-zinc-300 dark:hover:border-zinc-700'
                      }`}
                    >
                      <div className="capitalize">{t}</div>
                      {t === 'system' && (
                        <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                          ({resolvedTheme})
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>
        );
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <div className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Settings
        </h1>
        <p className="text-zinc-500 dark:text-zinc-400 mt-2 text-lg">
          Manage your account preferences and application settings.
        </p>
      </div>

      {message && (
        <div
          className={`mb-6 px-4 py-3 rounded-lg text-sm font-medium ${
            message.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400'
              : 'bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="flex flex-col md:flex-row gap-8">
        <div className="w-full md:w-64 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50'
                    : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900/50 hover:text-zinc-900 dark:hover:text-zinc-50'
                }`}
              >
                <tab.icon className="w-4 h-4" /> {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex-1">{renderTabContent()}</div>
      </div>
    </div>
  );
}
