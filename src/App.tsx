import { Navigate, Route, Routes } from "react-router-dom";
import { Forgot, Login, Register } from "./pages/Auth";
import Dashboard from "./pages/Dashboard";
import Landing from "./pages/Landing";
import Profile from "./pages/Profile";
import { useApp } from "./lib/store";
import type { ReactNode } from "react";

function Private({ children }: { children: ReactNode }) {
  const { user } = useApp();
  return user ? <>{children}</> : <Navigate to="/connexion" replace />;
}
function Public({ children }: { children: ReactNode }) {
  const { user } = useApp();
  return user ? <Navigate to="/tableau-de-bord" replace /> : <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Public><Landing /></Public>} />
      <Route path="/connexion" element={<Public><Login /></Public>} />
      <Route path="/inscription" element={<Public><Register /></Public>} />
      <Route path="/mot-de-passe-oublie" element={<Public><Forgot /></Public>} />
      <Route path="/tableau-de-bord" element={<Private><Dashboard /></Private>} />
      <Route path="/profil" element={<Private><Profile /></Private>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
