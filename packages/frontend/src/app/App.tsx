import React from 'react';
import { RouterProvider } from 'react-router';
import { router } from './routes';
import { useTheme } from './hooks/useTheme';
import { AuthProvider } from './auth/context';
import { SearchStateProvider } from './contexts/SearchStateContext';

export default function App() {
  // Initialize theme on app load
  useTheme();

  return (
    <AuthProvider>
      <SearchStateProvider>
        <div className="antialiased font-sans bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50 min-h-screen">
          <RouterProvider router={router} />
        </div>
      </SearchStateProvider>
    </AuthProvider>
  );
}
