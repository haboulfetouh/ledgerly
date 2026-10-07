import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { initKeycloak } from "./auth/keycloak";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

const rootElement = document.getElementById("root")!;
const root = createRoot(rootElement);

root.render(
  <div className="flex h-screen items-center justify-center text-sm text-slate-400">
    Loading…
  </div>,
);

// Being unauthenticated is a normal state here (not an error) — each
// tenant and the platform portal have their own in-app login page, so the
// router itself decides what to show once Keycloak has finished booting.
initKeycloak()
  .then(() => {
    root.render(
      <StrictMode>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </QueryClientProvider>
      </StrictMode>,
    );
  })
  .catch((err) => {
    console.error("Keycloak init failed", err);
    root.render(
      <div className="flex h-screen items-center justify-center text-sm text-rose-500">
        Could not reach the authentication server.
      </div>,
    );
  });
