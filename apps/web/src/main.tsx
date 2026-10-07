import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./theme/tokens.css";
import "./i18n";
import { App } from "./App";
import { applyTheme, usePrefs } from "./lib/prefs";

applyTheme(usePrefs.getState().theme);

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 1000, refetchOnWindowFocus: true } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
