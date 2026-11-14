/*
 * Connexion directe à Amazon Cognito (contrat : « le login se fait auprès de Cognito, pas via notre API »).
 * Flux USER_PASSWORD_AUTH, client d'application sans secret. Aucun mot de passe n'est conservé.
 */
import { ApiError } from "./errors";

const REGION = import.meta.env.VITE_COGNITO_REGION;
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID;
const KEY = "alphaforge.tokens";

type Tokens = { accessToken: string; refreshToken: string; expiresAt: number };

function read(): Tokens | null {
  try { return JSON.parse(sessionStorage.getItem(KEY) ?? "null"); } catch { return null; }
}
function write(t: Tokens | null) {
  if (t) sessionStorage.setItem(KEY, JSON.stringify(t)); else sessionStorage.removeItem(KEY);
}

async function cognito(target: string, body: unknown): Promise<any> {
  if (!REGION || !CLIENT_ID) throw new ApiError("INTERNAL", "Cognito n'est pas configuré (VITE_COGNITO_REGION, VITE_COGNITO_CLIENT_ID).", 0);
  let res: Response;
  try {
    res = await fetch(`https://cognito-idp.${REGION}.amazonaws.com/`, {
      method: "POST",
      headers: { "Content-Type": "application/x-amz-json-1.1", "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}` },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError("NETWORK", "Connexion à Cognito impossible.", 0);
  }
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    const type = String(json.__type ?? "");
    const msg = type.includes("NotAuthorized") || type.includes("UserNotFound") ? "Identifiants invalides." : json.message ?? "Échec de la connexion.";
    throw new ApiError("UNAUTHORIZED", msg, res.status);
  }
  return json;
}

function store(r: any, fallbackRefresh?: string): Tokens {
  const a = r.AuthenticationResult;
  const t: Tokens = {
    accessToken: a.AccessToken,
    refreshToken: a.RefreshToken ?? fallbackRefresh,
    expiresAt: Date.now() + (a.ExpiresIn ?? 3600) * 1000,
  };
  write(t);
  return t;
}

export async function signIn(username: string, password: string) {
  const r = await cognito("InitiateAuth", { AuthFlow: "USER_PASSWORD_AUTH", ClientId: CLIENT_ID, AuthParameters: { USERNAME: username, PASSWORD: password } });
  if (!r.AuthenticationResult) throw new ApiError("UNAUTHORIZED", "Cette connexion demande une étape supplémentaire (ex. changement de mot de passe). Contactez l'équipe.", 401);
  store(r);
}

export function signOut() { write(null); inflight = null; }
export const hasSession = () => read() !== null;

let inflight: Promise<string> | null = null;

/** Retourne un accessToken valide (renouvelé au besoin). Lève UNAUTHORIZED si la session est perdue. */
export async function getAccessToken(forceRefresh = false): Promise<string> {
  const t = read();
  if (!t) throw new ApiError("UNAUTHORIZED", "Session expirée.", 401);
  if (!forceRefresh && t.expiresAt - Date.now() > 30_000) return t.accessToken;
  inflight ??= cognito("InitiateAuth", { AuthFlow: "REFRESH_TOKEN_AUTH", ClientId: CLIENT_ID, AuthParameters: { REFRESH_TOKEN: t.refreshToken } })
    .then((r) => store(r, t.refreshToken).accessToken)
    .catch((e) => { write(null); throw e instanceof ApiError && e.code === "NETWORK" ? e : new ApiError("UNAUTHORIZED", "Session expirée.", 401); })
    .finally(() => { inflight = null; });
  return inflight;
}
