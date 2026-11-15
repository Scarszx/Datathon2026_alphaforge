/*
 * Connexion directe à Amazon Cognito (contrat : « le login se fait auprès de Cognito, pas via notre API »).
 * Flux USER_PASSWORD_AUTH, client d'application sans secret. Aucun mot de passe n'est conservé.
 */
import { DEMO, demoSignIn, demoSignUp } from "./demo";
import { ApiError } from "./errors";
import type { ErrorCode } from "./types";

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
    const type = String(json.__type ?? "").split("#").pop() ?? "";
    const known = COGNITO_ERRORS[type];
    if (known) throw new ApiError(known[0], known[1], res.status);
    throw new ApiError("UNAUTHORIZED", json.message ?? "Échec de la requête Cognito.", res.status);
  }
  return json;
}

/* Erreurs Cognito traduites (les messages bruts de Cognito sont en anglais). */
const COGNITO_ERRORS: Record<string, [ErrorCode, string]> = {
  NotAuthorizedException: ["UNAUTHORIZED", "Identifiants invalides."],
  UserNotFoundException: ["UNAUTHORIZED", "Identifiants invalides."],
  UserNotConfirmedException: ["UNAUTHORIZED", "Ce compte n'est pas encore confirmé. Entrez le code reçu par courriel."],
  UsernameExistsException: ["VALIDATION_ERROR", "Ce nom d'utilisateur est déjà pris."],
  InvalidPasswordException: ["VALIDATION_ERROR", "Mot de passe refusé : au moins 8 caractères avec majuscule, minuscule, chiffre et symbole."],
  InvalidParameterException: ["VALIDATION_ERROR", "Un des champs est invalide (vérifiez le courriel et le nom d'utilisateur)."],
  CodeMismatchException: ["VALIDATION_ERROR", "Code de confirmation invalide."],
  ExpiredCodeException: ["VALIDATION_ERROR", "Ce code a expiré. Demandez-en un nouveau."],
  LimitExceededException: ["VALIDATION_ERROR", "Trop de tentatives. Réessayez dans quelques minutes."],
  TooManyRequestsException: ["VALIDATION_ERROR", "Trop de tentatives. Réessayez dans quelques minutes."],
};

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
  if (DEMO) { write({ accessToken: demoSignIn(username, password), refreshToken: "", expiresAt: Date.now() + 365 * 86400000 }); return; }
  const r = await cognito("InitiateAuth", { AuthFlow: "USER_PASSWORD_AUTH", ClientId: CLIENT_ID, AuthParameters: { USERNAME: username, PASSWORD: password } });
  if (!r.AuthenticationResult) throw new ApiError("UNAUTHORIZED", "Cette connexion demande une étape supplémentaire (ex. changement de mot de passe). Contactez l'équipe.", 401);
  store(r);
}

/**
 * Inscription Cognito (SignUp, public, sans jeton). Retourne `true` si le compte est déjà confirmé
 * (pool à confirmation automatique), sinon un code est envoyé par courriel et doit passer par confirmSignUp.
 */
export async function signUp(username: string, password: string, email: string, givenName: string, familyName: string): Promise<boolean> {
  if (DEMO) { demoSignUp(username, password, email, `${givenName} ${familyName}`); return true; } // compte confirmé d'office
  // Attributs standard Cognito; le client d'application doit avoir le droit d'écrire given_name et family_name.
  const r = await cognito("SignUp", {
    ClientId: CLIENT_ID, Username: username, Password: password,
    UserAttributes: [
      { Name: "email", Value: email },
      { Name: "given_name", Value: givenName },
      { Name: "family_name", Value: familyName },
    ],
  });
  return r.UserConfirmed === true;
}

export async function confirmSignUp(username: string, code: string) {
  await cognito("ConfirmSignUp", { ClientId: CLIENT_ID, Username: username, ConfirmationCode: code });
}

export async function resendCode(username: string) {
  await cognito("ResendConfirmationCode", { ClientId: CLIENT_ID, Username: username });
}

export function signOut() { write(null); inflight = null; }
export const hasSession = () => read() !== null;

let inflight: Promise<string> | null = null;

/** Retourne un accessToken valide (renouvelé au besoin). Lève UNAUTHORIZED si la session est perdue. */
export async function getAccessToken(forceRefresh = false): Promise<string> {
  const t = read();
  if (!t) throw new ApiError("UNAUTHORIZED", "Session expirée.", 401);
  if (!forceRefresh && t.expiresAt - Date.now() > 30_000) return t.accessToken;
  if (DEMO) { write(null); throw new ApiError("UNAUTHORIZED", "Session expirée.", 401); } // pas de renouvellement en démo
  inflight ??= cognito("InitiateAuth", { AuthFlow: "REFRESH_TOKEN_AUTH", ClientId: CLIENT_ID, AuthParameters: { REFRESH_TOKEN: t.refreshToken } })
    .then((r) => store(r, t.refreshToken).accessToken)
    .catch((e) => { write(null); throw e instanceof ApiError && e.code === "NETWORK" ? e : new ApiError("UNAUTHORIZED", "Session expirée.", 401); })
    .finally(() => { inflight = null; });
  return inflight;
}
