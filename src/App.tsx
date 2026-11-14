import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useApp } from "./lib/store";
import ChatWidget from "./components/ChatWidget";
import Login from "./pages/Login";
import Markets from "./pages/Markets";
import Portfolio from "./pages/Portfolio";
import Profile from "./pages/Profile";

/* Aucune route publique côté API; seul /login est accessible sans session. */
function Private({ children }: { children: ReactNode }) {
  const { status } = useApp();
  if (status === "loading") return <p className="muted" style={{ padding: 48 }}>Chargement…</p>;
  return status === "authed" ? <>{children}<ChatWidget /></> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/portefeuille" element={<Private><Portfolio /></Private>} />
      <Route path="/marches" element={<Private><Markets /></Private>} />
      <Route path="/profil" element={<Private><Profile /></Private>} />
      <Route path="*" element={<Navigate to="/portefeuille" replace />} />
    </Routes>
  );
}
