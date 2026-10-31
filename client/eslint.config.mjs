import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __dirname = dirname(fileURLToPath(import.meta.url));

const compat = new FlatCompat({ baseDirectory: __dirname });

// Frontiers between modules: documentation/frontieres-front.md
const CLIENT_UNIQUE = { group: ["axios"], message: "Les appels passent par le client unique : @/lib/api." };
const PAR_INDEX = { group: ["@/features/*/*"], message: "Un module s'importe par son index : @/features/<module>." };
const SANS_MODULES = { group: ["@/features/*", "@/components/*"], message: "lib/ est partagé par tous les modules : il ne dépend d'aucun." };
const FONCTIONS_DE_LANGUE = {
  name: "@/lib/utils",
  importNames: ["formatDate", "formatPrice", "formatFcfa", "selon", "langue", "TYPE_LABELS", "ROLE_LABELS"],
  message: "Dans un composant, utiliser useFormat (lib/format.ts) : ces fonctions ne suivent la langue que dans le navigateur.",
};

// A file gets the last block that names a rule: each block below repeats what still applies to it
const eslintConfig = [
  {
    ignores: ["node_modules/**", ".next/**", "out/**", "build/**", "next-env.d.ts"],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: { "no-restricted-imports": ["error", { patterns: [CLIENT_UNIQUE, PAR_INDEX] }] },
  },
  {
    // The back-office and the agents' space stay in French
    files: ["src/app/*locale*/**/*.{ts,tsx}", "src/components/**/*.{ts,tsx}", "src/features/**/*.{ts,tsx}"],
    ignores: ["src/components/backoffice/**", "src/components/agent/**", "src/features/*/admin/**"],
    rules: { "no-restricted-imports": ["error", { paths: [FONCTIONS_DE_LANGUE], patterns: [CLIENT_UNIQUE, PAR_INDEX] }] },
  },
  {
    files: ["src/lib/**/*.{ts,tsx}"],
    ignores: ["src/lib/api.ts"],
    rules: { "no-restricted-imports": ["error", { patterns: [CLIENT_UNIQUE, SANS_MODULES] }] },
  },
  {
    files: ["src/lib/api.ts"],
    rules: { "no-restricted-imports": "off" },
  },
  {
    // Migration in progress: the number of warnings shows what is left
    files: ["src/app/**/*.{ts,tsx}", "src/components/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-syntax": ["warn", {
        selector: "ImportDeclaration[source.value='@/lib/api'] > ImportDefaultSpecifier",
        message: "Les appels à l'API d'un module vont dans features/<module>/api.ts.",
      }],
    },
  },
];

export default eslintConfig;
