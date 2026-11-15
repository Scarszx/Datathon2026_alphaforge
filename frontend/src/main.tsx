import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AppProvider } from "./lib/store";
import "./styles.css";

/* Derrière le proxy de l'IDE (…/proxy/4173/), les routes vivent sous ce préfixe. Ailleurs : racine. */
const basename = window.location.pathname.match(/^\/(?:abs)?proxy\/\d+/)?.[0] ?? "/";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <AppProvider>
        <App />
      </AppProvider>
    </BrowserRouter>
  </StrictMode>,
);
