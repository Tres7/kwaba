import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __dirname = dirname(fileURLToPath(import.meta.url));

const compat = new FlatCompat({ baseDirectory: __dirname });

const eslintConfig = [
  {
    ignores: ["node_modules/**", ".next/**", "out/**", "build/**", "next-env.d.ts"],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    // The back-office and the agents' space stay in French
    files: ["src/app/*locale*/**/*.{ts,tsx}", "src/components/**/*.{ts,tsx}"],
    ignores: ["src/components/backoffice/**", "src/components/agent/**"],
    rules: {
      "no-restricted-imports": ["error", {
        paths: [{
          name: "@/lib/utils",
          importNames: ["formatDate", "formatPrice", "formatFcfa", "selon", "langue", "TYPE_LABELS", "ROLE_LABELS"],
          message: "Dans un composant, utiliser useFormat (lib/format.ts) : ces fonctions ne suivent la langue que dans le navigateur.",
        }],
      }],
    },
  },
];

export default eslintConfig;
