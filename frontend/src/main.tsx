import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { UIProvider } from "./context/ui";
import { ThemeProvider } from "./context/theme";
import "@fontsource-variable/inter";
import "@fontsource-variable/fraunces";
import "@fontsource-variable/fraunces/wght-italic.css";
import "./styles/global.css";
import "./styles/theme-and-ui.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <UIProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </UIProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
