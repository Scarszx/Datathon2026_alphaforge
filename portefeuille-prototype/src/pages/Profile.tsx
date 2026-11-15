import { useState } from "react";
import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import Questionnaire, { ProfileSummary } from "../components/Questionnaire";
import { useApp } from "../lib/store";

export default function Profile() {
  const { user, data, saveProfile } = useApp();
  const [editing, setEditing] = useState(false);
  const [saved, setSaved] = useState(false);
  const p = data!.profile;
  return (
    <>
      <AppHeader />
      <main className="wrap" style={{ maxWidth: 760 }}>
        <div className="stock-hero"><div><Link to="/tableau-de-bord" className="chip-back">← Tableau de bord</Link><h1 className="auth-h" style={{ marginTop: 16 }}>Mon profil</h1><div className="meta">{user?.firstName} {user?.lastName} · {user?.email} · @{user?.username}</div></div></div>
        {saved && <div className="banner ok" style={{ marginBottom: 20 }}>Profil mis à jour.</div>}
        {editing ? (
          <Questionnaire initial={p.answers} optional submitLabel="Enregistrer" onSubmit={(a) => { saveProfile(a); setEditing(false); setSaved(true); }} />
        ) : (
          <>
            <ProfileSummary answers={p.answers} />
            <dl className="kv" style={{ marginTop: 24 }}>
              <div><dt>Classification</dt><dd>{p.label}</dd></div>
              <div><dt>Score de risque</dt><dd>{p.score} / 100</dd></div>
              <div><dt>Objectif</dt><dd>{p.objective}</dd></div>
              <div><dt>Horizon</dt><dd>{p.horizon}</dd></div>
              <div><dt>Expérience</dt><dd>{p.experience}</dd></div>
              <div><dt>Mise à jour</dt><dd>{new Date(p.updatedAt).toLocaleDateString("fr-CA")}</dd></div>
            </dl>
            <div style={{ margin: "24px 0 64px" }}><button type="button" className="btn" onClick={() => { setSaved(false); setEditing(true); }}>Modifier mon profil</button></div>
          </>
        )}
      </main>
    </>
  );
}
