import React, { useState, useEffect } from 'react';
import { User, Bell, Shield, Palette } from 'lucide-react';
import { fetchSettings, updateSettings, type SettingsData } from '../api';

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  // Local form state
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [autoSummarize, setAutoSummarize] = useState(true);
  const [includeReadmes, setIncludeReadmes] = useState(true);

  useEffect(() => {
    fetchSettings()
      .then((data) => {
        setSettings(data);
        setFirstName(data.first_name);
        setLastName(data.last_name);
        setEmail(data.email);
        setAutoSummarize(data.auto_summarize);
        setIncludeReadmes(data.include_readmes);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      const updated = await updateSettings({
        first_name: firstName,
        last_name: lastName,
        email,
        auto_summarize: autoSummarize,
        include_readmes: includeReadmes,
      });
      setSettings(updated);
      setMessage('Settings saved successfully.');
      setTimeout(() => setMessage(''), 3000);
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin" />
      </div>
    );
  }

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

      <div className="flex flex-col md:flex-row gap-8">
        <div className="w-full md:w-64 flex-shrink-0">
          <nav className="space-y-1">
            <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 transition-colors">
              <User className="w-4 h-4" /> Account
            </button>
            <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900/50 hover:text-zinc-900 dark:hover:text-zinc-50 transition-colors">
              <Palette className="w-4 h-4" /> Appearance
            </button>
            <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900/50 hover:text-zinc-900 dark:hover:text-zinc-50 transition-colors">
              <Bell className="w-4 h-4" /> Notifications
            </button>
            <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900/50 hover:text-zinc-900 dark:hover:text-zinc-50 transition-colors">
              <Shield className="w-4 h-4" /> Security
            </button>
          </nav>
        </div>

        <div className="flex-1 space-y-8">
          <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
            <div className="px-6 py-5 border-b border-zinc-200 dark:border-zinc-800">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">Profile Information</h2>
            </div>
            <div className="p-6 space-y-6">
              <div className="flex items-center gap-6">
                <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-500 flex items-center justify-center text-white text-2xl font-bold shadow-md">
                  {firstName && lastName ? `${firstName[0]}${lastName[0]}` : 'SM'}
                </div>
                <div>
                  <button className="px-4 py-2 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-900 dark:text-zinc-50 rounded-xl font-medium transition-colors text-sm border border-zinc-200 dark:border-zinc-700 mb-2">
                    Change Avatar
                  </button>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">JPG, GIF or PNG. 1MB max.</p>
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
              </div>
            </div>
            <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
              {message && (
                <span className={`text-sm ${message.startsWith('Error') ? 'text-red-500' : 'text-emerald-500'}`}>
                  {message}
                </span>
              )}
              <div className="flex-1" />
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-5 py-2 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 rounded-xl font-medium transition-colors text-sm shadow-sm disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </section>

          <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
            <div className="px-6 py-5 border-b border-zinc-200 dark:border-zinc-800">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">AI Preferences</h2>
            </div>
            <div className="p-6 space-y-4">
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
                  <div className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">Automatically generate AI tags and summaries when a new starred repository is synced.</div>
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
                  <div className="font-medium text-sm text-zinc-900 dark:text-zinc-50">Include repository readmes in search</div>
                  <div className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">This improves search quality but increases processing time.</div>
                </div>
              </label>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
