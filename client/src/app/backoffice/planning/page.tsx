"use client";

import AgentPlanning from "@/features/agenda/admin/AgentPlanning";

export default function AgentPlanningPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Planning des agents</h1>
        <p className="text-muted text-sm mt-1">Disponibilités, indisponibilités et visites de chaque agent, jour par jour.</p>
      </div>
      <AgentPlanning />
    </div>
  );
}
