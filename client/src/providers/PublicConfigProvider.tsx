"use client";

import { createContext, useContext } from "react";
import { CONTACT_EMAIL_DEFAUT, type ConfigPublique } from "@/lib/public-config";

const Contexte = createContext<ConfigPublique>({ contactEmail: CONTACT_EMAIL_DEFAUT, googleClientId: "" });

/** Public values of the environment for the client components (values read by the server, lib/public-config.ts). */
export default function PublicConfigProvider({ value, children }: { value: ConfigPublique; children: React.ReactNode }) {
  return <Contexte.Provider value={value}>{children}</Contexte.Provider>;
}

export function useConfigPublique(): ConfigPublique {
  return useContext(Contexte);
}
