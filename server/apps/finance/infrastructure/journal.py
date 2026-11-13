"""Sensitive actions of the finance module in the activity log (module activity), append only for the application
role. The rate changes and payouts of FIN-13.3 will join this adapter."""
from apps.finance.application.ports import Journal
from apps.activity import api as activity


class AuditJournal(Journal):
    def correction(self, par_id, mouvement_id: int, inverse_id: int, motif: str) -> None:
        activity.record('ecriture_corrigee', actor=par_id, mouvement=mouvement_id, ligne_inverse=inverse_id,
                        motif=motif)
