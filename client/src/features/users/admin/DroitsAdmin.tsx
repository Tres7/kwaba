"use client";

import { modifierUtilisateurAdmin } from "../api";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import Panneau, { Champ, Interrupteur, Saisie, erreursApi } from "@/components/backoffice/Panneau";
import type { AdminUser, DroitsAdmin as Droits } from "@/types/api/admin";

/** Local date and time for the datetime-local field. */
function pourSaisie(iso: string | null) {
  if (!iso) return "";
  const date = new Date(iso);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

/** Rights of an admin, set by a super admin: sections opened and end of a temporary access. */
export default function DroitsAdmin({ admin, sections, onFermer }: {
  admin: AdminUser | null; sections: Droits["sections_disponibles"]; onFermer: () => void;
}) {
  const queryClient = useQueryClient();
  const [limite, setLimite] = useState(!!admin?.admin_sections);
  const [choisies, setChoisies] = useState<string[]>(admin?.admin_sections ?? []);
  const [fin, setFin] = useState(pourSaisie(admin?.admin_expire_le ?? null));
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  const basculer = (code: string, coche: boolean) =>
    setChoisies(coche ? [...choisies, code] : choisies.filter((c) => c !== code));

  const valider = async () => {
    if (!admin) return;
    setEnvoi(true);
    setErreurs({});
    try {
      await modifierUtilisateurAdmin(admin.id, {
        admin_sections: limite ? choisies : null,
        admin_expire_le: fin ? new Date(fin).toISOString() : null,
      });
      toast.success("Droits mis à jour");
      queryClient.invalidateQueries({ queryKey: ["admin"] });
      onFermer();
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const nom = admin ? `${admin.first_name} ${admin.last_name}`.trim() || admin.email : "";
  return (
    <Panneau ouvert={!!admin} titre={`Droits de ${nom}`} onFermer={onFermer} onValider={valider} envoi={envoi}>
      {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
      <Interrupteur label="Limiter à certaines sections" checked={limite} onChange={setLimite} />
      {limite && (
        <fieldset className="space-y-2">
          <legend className="text-xs font-bold text-dark uppercase tracking-wide mb-2">Sections ouvertes</legend>
          {sections.map(({ code, libelle }) => (
            <label key={code} className="flex items-center gap-2 text-sm text-dark">
              <input type="checkbox" checked={choisies.includes(code)} onChange={(e) => basculer(code, e.target.checked)} />
              {libelle}
            </label>
          ))}
          {erreurs.admin_sections && <p role="alert" className="text-sm text-red-700">{erreurs.admin_sections}</p>}
        </fieldset>
      )}
      <Champ label="Fin de l'accès" erreur={erreurs.admin_expire_le} aide="Vide : pas de limite. À cette date, le compte retrouve son rôle précédent.">
        <Saisie type="datetime-local" value={fin} onChange={(e) => setFin(e.target.value)} />
      </Champ>
    </Panneau>
  );
}
