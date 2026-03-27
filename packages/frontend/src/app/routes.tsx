import { createBrowserRouter } from "react-router";
import { lazy, Suspense } from "react";
import { Layout } from "./components/Layout";

// Lazy load page components for code splitting
const SearchPage = lazy(() => import("./pages/SearchPage").then(m => ({ default: m.SearchPage })));
const RepositoriesPage = lazy(() => import("./pages/RepositoriesPage").then(m => ({ default: m.RepositoriesPage })));
const RepositoryDetailPage = lazy(() => import("./pages/RepositoryDetailPage").then(m => ({ default: m.RepositoryDetailPage })));
const SyncCenterPage = lazy(() => import("./pages/SyncCenterPage").then(m => ({ default: m.SyncCenterPage })));
const SettingsPage = lazy(() => import("./pages/SettingsPage").then(m => ({ default: m.SettingsPage })));
const CollectionsPage = lazy(() => import("./pages/CollectionsPage").then(m => ({ default: m.CollectionsPage })));
const CollectionDetailPage = lazy(() => import("./pages/CollectionDetailPage").then(m => ({ default: m.CollectionDetailPage })));
const ArchivesPage = lazy(() => import("./pages/ArchivesPage").then(m => ({ default: m.ArchivesPage })));
const DashboardPage = lazy(() => import("./pages/DashboardPage").then(m => ({ default: m.DashboardPage })));
const PublicSharedPage = lazy(() => import("./pages/PublicSharedPage").then(m => ({ default: m.PublicSharedPage })));
const SharedArchivePage = lazy(() => import("./pages/SharedArchivePage").then(m => ({ default: m.SharedArchivePage })));

// Loading fallback component
function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="w-8 h-8 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin" />
    </div>
  );
}

// Wrapper for lazy components with Suspense
function LazyPage({ Component }: { Component: React.LazyExoticComponent<React.ComponentType> }) {
  return (
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  {
    path: "/shared/:shareId",
    element: <LazyPage Component={PublicSharedPage} />,
  },
  {
    path: "/share/:shareId",
    element: <LazyPage Component={SharedArchivePage} />,
  },
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, element: <LazyPage Component={SearchPage} /> },
      { path: "dashboard", element: <LazyPage Component={DashboardPage} /> },
      { path: "repositories", element: <LazyPage Component={RepositoriesPage} /> },
      { path: "repositories/:id", element: <LazyPage Component={RepositoryDetailPage} /> },
      { path: "sync", element: <LazyPage Component={SyncCenterPage} /> },
      { path: "settings", element: <LazyPage Component={SettingsPage} /> },
      { path: "collections", element: <LazyPage Component={CollectionsPage} /> },
      { path: "collections/:id", element: <LazyPage Component={CollectionDetailPage} /> },
      { path: "archives", element: <LazyPage Component={ArchivesPage} /> },
    ],
  },
]);
