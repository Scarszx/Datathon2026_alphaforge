/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL de base d'API Gateway, sans « /v1 » (ex. https://abc.execute-api.ca-central-1.amazonaws.com) */
  readonly VITE_API_BASE_URL: string;
  /** Région du user pool Cognito (région « A_CONFIRMER » dans le contrat) */
  readonly VITE_COGNITO_REGION: string;
  /** Client d'application Cognito (sans secret) */
  readonly VITE_COGNITO_CLIENT_ID: string;
  /** « 1 » : mode démo local (src/api/demo.ts), sans Cognito ni API */
  readonly VITE_DEMO?: string;
}
