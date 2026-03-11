import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { SearchPage } from "./pages/SearchPage";
import { RepositoriesPage } from "./pages/RepositoriesPage";
import { RepositoryDetailPage } from "./pages/RepositoryDetailPage";
import { SyncCenterPage } from "./pages/SyncCenterPage";
import { SettingsPage } from "./pages/SettingsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: SearchPage },
      { path: "repositories", Component: RepositoriesPage },
      { path: "repositories/:id", Component: RepositoryDetailPage },
      { path: "sync", Component: SyncCenterPage },
      { path: "settings", Component: SettingsPage },
    ],
  },
]);
