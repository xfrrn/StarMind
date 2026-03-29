import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '../auth/context';

export function OAuthCallbackPage() {
    const navigate = useNavigate();
    const { loginWithGithub } = useAuth();
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const handleCallback = async () => {
            const params = new URLSearchParams(window.location.search);
            const code = params.get('code');
            const state = params.get('state');

            if (!code || !state) {
                navigate('/login');
                return;
            }

            try {
                await loginWithGithub(code, state);
                navigate('/');
            } catch (err) {
                console.error('GitHub login failed:', err);
                setError(err instanceof Error ? err.message : 'GitHub 登录失败');
            }
        };

        handleCallback();
    }, [navigate, loginWithGithub]);

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-900">
                <div className="max-w-md w-full p-8 bg-white dark:bg-zinc-800 rounded-2xl shadow-lg text-center">
                    <h2 className="text-xl font-bold text-red-500 mb-4">登录失败</h2>
                    <p className="text-zinc-600 dark:text-zinc-400 mb-6">{error}</p>
                    <button
                        onClick={() => navigate('/login')}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                        返回登录
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-900">
            <div className="text-center">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">正在连接 GitHub...</h2>
                <p className="text-sm text-zinc-500 mt-2">请稍候</p>
            </div>
        </div>
    );
}
