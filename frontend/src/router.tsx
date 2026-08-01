import { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";

// Default cache lifetimes for the whole app. Individual queries can still
// override staleTime for data that changes faster (e.g. job search results)
// or slower (e.g. static reference data) than this baseline.
const DEFAULT_STALE_TIME = 30_000; // 30s: data is "fresh enough" to skip a refetch
const DEFAULT_GC_TIME = 5 * 60_000; // 5min: how long unused cache entries survive

export const getRouter = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: DEFAULT_STALE_TIME,
        gcTime: DEFAULT_GC_TIME,
        retry: 2,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
      },
      mutations: {
        retry: 0,
      },
    },
  });

  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    // Match router-level preload freshness to the query cache's staleTime so
    // hovering a link can actually reuse an already-fresh query instead of
    // treating every preload as stale (the previous value of 0 disabled this).
    defaultPreloadStaleTime: DEFAULT_STALE_TIME,
    defaultPreload: "intent",
  });

  return router;
};
