/* Déclarations minimales pour les tests qui lisent les fichiers du backend (contrat fait foi).
 * `@types/node` n'est pas une dépendance du front : ne déclarer que ce que front-ae.test.tsx utilise. */
declare module "node:fs" {
  export function readFileSync(path: string, encoding: string): string;
}
declare module "node:path" {
  export function resolve(...segments: string[]): string;
}
declare const process: { cwd(): string };
