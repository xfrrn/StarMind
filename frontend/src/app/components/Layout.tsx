import React from 'react';
import { Outlet } from 'react-router';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

export function Layout() {
  return (
    <div className="flex h-screen w-full bg-white dark:bg-zinc-950 overflow-hidden font-sans selection:bg-blue-100 dark:selection:bg-blue-900/30">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-zinc-950">
        <Header />
        <main className="flex-1 overflow-auto bg-white dark:bg-zinc-950 relative z-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
