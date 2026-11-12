"use client";

import AgendaSettings from "@/features/agenda/admin/AgendaSettings";

export default function AgendaSettingsPage() {
  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Réglages de l&apos;agenda</h1>
        <p className="text-muted text-sm mt-1">Règles des visites de vérification, modifiables sans nouveau déploiement.</p>
      </div>
      <AgendaSettings />
    </div>
  );
}
