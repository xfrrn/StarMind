import React from 'react';
import { RouterProvider } from 'react-router';
import { router } from './routes';

export default function App() {
  return (
    <div className="antialiased font-sans bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50 min-h-screen">
      <RouterProvider router={router} />
    </div>
  );
}
