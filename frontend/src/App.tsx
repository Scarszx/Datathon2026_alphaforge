import { Navigate, Route, Routes } from "react-router-dom";
import AssetPage from "./pages/AssetPage";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Markets from "./pages/Markets";
import Portfolio from "./pages/Portfolio";
import Profile from "./pages/Profile";
import Register from "./pages/Register";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/inscription" element={<Register />} />
      <Route path="/accueil" element={<Dashboard />} />
      <Route path="/chat" element={<Chat />} />
      <Route path="/portefeuille" element={<Portfolio />} />
      <Route path="/marches" element={<Markets />} />
      <Route path="/marches/:ticker" element={<AssetPage />} />
      <Route path="/profil" element={<Profile />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
