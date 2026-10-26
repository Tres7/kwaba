"""Contract signature (personal link or host space) and management in the back-office."""
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config import prelancement
from apps.documents.models import ParametresSocieteModel
from apps.securite.audit import journaliser
from apps.securite.limites import ip_client, limite_ip
from apps.securite.permissions import EstAdministrateur

from . import preinscription, services
from .models import TYPES, ContratModel, ModeleContratModel
from .pdf import contrat_pdf

LimiteLecture = limite_ip('contrat', 120, 3600)
LimiteSignature = limite_ip('contrat_signature', 20, 3600)


def _pdf(contrat: ContratModel) -> HttpResponse:
    contenu = contrat.pdf.read() if contrat.statut == 'signe' and contrat.pdf else contrat_pdf(contrat)
    reponse = HttpResponse(contenu, content_type='application/pdf')
    reponse['Content-Disposition'] = f'attachment; filename="contrat-{contrat.reference}.pdf"'
    reponse['Cache-Control'] = 'no-store'
    reponse['X-Content-Type-Options'] = 'nosniff'
    return reponse


def _public(c: ContratModel) -> dict:
    """What the signer sees (never the technical proofs nor the internal id)."""
    return {
        'reference': c.reference, 'titre': c.titre, 'type': c.type, 'type_libelle': c.get_type_display(),
        'statut': c.statut, 'partie_nom': c.partie_nom, 'kwaba_signataire': c.kwaba_signataire,
        'version': c.version_modele, 'blocs': services.blocs(c.corps), 'expire_le': c.expire_le,
        'expire': c.statut == 'a_signer' and c.expire_le < timezone.now(),
        'signe_le': c.signe_le, 'signataire_nom': c.signataire_nom,
    }


def _signer(request, contrat, methode):
    try:
        contrat = services.signer(
            contrat, nom=str(request.data.get('nom', '')), signature=request.data.get('signature', ''),
            accepte=request.data.get('accepte') is True, ip=ip_client(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''), methode=methode,
        )
    except services.ContratErreur as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    journaliser('contrat_signe', request, utilisateur=request.user if request.user.is_authenticated else None,
                email=contrat.partie_email, contrat=contrat.reference, type=contrat.type)
    return Response(_public(contrat))


# --- Personal link (rental company, driver, NGO, or host invited by email) ----------------------------

class SignaturePubliqueView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LimiteLecture]

    def get(self, request, jeton):
        contrat = services.par_jeton(jeton)
        if not contrat:
            return Response({'detail': 'Lien invalide ou contrat annulé.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_public(contrat))


class SignaturePubliquePdfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LimiteLecture]

    def get(self, request, jeton):
        contrat = services.par_jeton(jeton)
        if not contrat:
            return Response({'detail': 'Lien invalide ou contrat annulé.'}, status=status.HTTP_404_NOT_FOUND)
        return _pdf(contrat)


class SignerPubliqueView(APIView):
    """POST {nom, signature (image en data URL), accepte: true}."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LimiteSignature]

    def post(self, request, jeton):
        contrat = services.par_jeton(jeton)
        if not contrat:
            return Response({'detail': 'Lien invalide ou contrat annulé.'}, status=status.HTTP_404_NOT_FOUND)
        return _signer(request, contrat, 'lien personnel')


# --- Host space -----------------------------------------------------------------------------------

def _apercu_hote(user) -> dict | None:
    """Contract the host is going to sign: theirs if it exists, otherwise the text that will be issued at signature."""
    contrat = ContratModel.objects.filter(hote=user).exclude(statut='annule').first()
    if contrat:
        return _public(contrat)
    type_contrat = services.type_contrat_hote(user)
    modele = ModeleContratModel.objects.filter(type=type_contrat).first()
    # The host agreement is offered once the company is registered (RCCM and NIF), as the pre-registration says
    if not modele or not ParametresSocieteModel.courants().immatriculee:
        return None
    infos = services.partie(type_contrat, user)
    return {
        'reference': None, 'titre': modele.titre, 'type': type_contrat, 'type_libelle': modele.get_type_display(), 'statut': 'a_signer',
        'partie_nom': infos['nom'], 'kwaba_signataire': '', 'version': modele.version,
        'blocs': services.blocs(services.rendre(modele.corps, services.contexte(type_contrat, infos))),
        'expire_le': None, 'expire': False, 'signe_le': None, 'signataire_nom': '',
    }


class EstHote(IsAuthenticated):
    message = "Réservé aux hôtes."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'hote'


class ContratHoteView(APIView):
    """GET: host contract of the signed-in user (404 while Kwa-Ba has not filled in its legal information)."""
    permission_classes = [EstHote]

    def get(self, request):
        apercu = _apercu_hote(request.user)
        if not apercu:
            return Response({'detail': 'Le contrat hôte sera bientôt disponible.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(apercu)


class SignerHoteView(APIView):
    """POST {nom, signature, accepte, version}: issues the contract (if it is not yet) then signs it."""
    permission_classes = [EstHote]
    throttle_classes = [LimiteSignature]

    def post(self, request):
        if not request.user.phone:
            return Response({'detail': 'Ajoutez votre numéro de téléphone (Profil) avant de signer : il figure au contrat.'},
                            status=status.HTTP_400_BAD_REQUEST)
        apercu = _apercu_hote(request.user)
        if not apercu:
            return Response({'detail': 'Le contrat hôte sera bientôt disponible.'}, status=status.HTTP_404_NOT_FOUND)
        if apercu['statut'] == 'signe':
            return Response({'detail': 'Votre contrat est déjà signé.'}, status=status.HTTP_400_BAD_REQUEST)
        # The text may have changed since the host read it: they sign what they read, or read again
        if str(request.data.get('version')) != str(apercu['version']):
            return Response({'detail': 'Le contrat vient d\'être mis à jour : relisez-le avant de signer.', 'code': 'version'},
                            status=status.HTTP_409_CONFLICT)
        try:
            contrat = services.contrat_hote(request.user)
        except services.ContratErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return _signer(request, contrat, 'compte Kwa-Ba')


class ContratHotePdfView(APIView):
    permission_classes = [EstHote]

    def get(self, request):
        contrat = ContratModel.objects.filter(hote=request.user).exclude(statut='annule').first()
        if not contrat:
            return Response({'detail': 'Aucun contrat.'}, status=status.HTTP_404_NOT_FOUND)
        return _pdf(contrat)


# --- Back-office -----------------------------------------------------------------------------------

def _admin(c: ContratModel) -> dict:
    return {
        'id': str(c.id), 'reference': c.reference, 'type': c.type, 'type_libelle': c.get_type_display(),
        'titre': c.titre, 'statut': c.statut, 'statut_libelle': c.get_statut_display(),
        'partie_nom': c.partie_nom, 'partie_email': c.partie_email, 'partie_telephone': c.partie_telephone,
        'cree_le': c.cree_le, 'envoye_le': c.envoye_le, 'expire_le': c.expire_le,
        'expire': c.statut == 'a_signer' and c.expire_le < timezone.now(),
        'signe_le': c.signe_le, 'signataire_nom': c.signataire_nom, 'ip': c.ip, 'methode': c.methode,
        'empreinte_pdf': c.empreinte_pdf, 'motif_annulation': c.motif_annulation, 'version_modele': c.version_modele,
    }


def _cible(type_contrat: str, pk):
    from django.contrib.auth import get_user_model
    from django.core.exceptions import ValidationError

    from apps.give.models import OrganisationModel
    from apps.locations.models import PartenaireLocationModel
    from apps.transferts.models import ChauffeurModel

    modeles = {'hote': get_user_model(), 'hotel': get_user_model(), 'chauffeur': ChauffeurModel, 'loueur': PartenaireLocationModel, 'ong': OrganisationModel}
    try:
        return modeles[type_contrat].objects.filter(pk=pk).first()
    except (ValueError, TypeError, ValidationError):
        return None


class ContratsAdminView(APIView):
    """GET: contracts (q, type, statut). POST {type, partie_id}: issues the contract and sends the signature link."""
    permission_classes = [EstAdministrateur]

    def get(self, request):
        from apps.backoffice.views import _paginer

        qs = ContratModel.objects.all()
        if q := request.query_params.get('q', '').strip():
            qs = qs.filter(Q(reference__icontains=q) | Q(partie_nom__icontains=q) | Q(partie_email__icontains=q))
        if (type_contrat := request.query_params.get('type')) in dict(TYPES):
            qs = qs.filter(type=type_contrat)
        if (statut := request.query_params.get('statut')) in dict(ContratModel.STATUTS):
            qs = qs.filter(statut=statut)
        return _paginer(request, qs.order_by('-cree_le'), _admin)

    def post(self, request):
        type_contrat = request.data.get('type')
        if type_contrat not in dict(TYPES):
            return Response({'type': ['Type de contrat inconnu.']}, status=status.HTTP_400_BAD_REQUEST)
        cible = _cible(type_contrat, request.data.get('partie_id'))
        if not cible or (type_contrat in services.TYPES_HOTE and cible.role not in ('hote', 'voyageur')):
            return Response({'partie_id': ['Partie introuvable.']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            contrat = services.emettre(type_contrat, cible, par=request.user)
        except services.ContratErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        journaliser('backoffice_creation', request, utilisateur=request.user, objet='contrat', id=str(contrat.pk), libelle=contrat.reference)
        return Response(_admin(contrat), status=status.HTTP_201_CREATED)


class PartiesAdminView(APIView):
    """Possible parties for a contract type (?type=, ?q=), with the state of their contract."""
    permission_classes = [EstAdministrateur]

    def get(self, request):
        from django.contrib.auth import get_user_model

        from apps.give.models import OrganisationModel
        from apps.locations.models import PartenaireLocationModel
        from apps.transferts.models import ChauffeurModel

        type_contrat = request.query_params.get('type')
        q = request.query_params.get('q', '').strip()
        if type_contrat in services.TYPES_HOTE:
            qs = get_user_model().objects.filter(role='hote', is_active=True)
            if q:
                qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
            lignes = [(u.pk, services._nom(u), u.email) for u in qs.order_by('first_name')[:30]]
        elif type_contrat == 'chauffeur':
            qs = ChauffeurModel.objects.filter(actif=True)
            if q:
                qs = qs.filter(Q(nom__icontains=q) | Q(prenom__icontains=q))
            lignes = [(c.pk, f"{c.prenom} {c.nom}", c.email) for c in qs.order_by('prenom')[:30]]
        elif type_contrat == 'loueur':
            qs = PartenaireLocationModel.objects.filter(actif=True)
            if q:
                qs = qs.filter(nom__icontains=q)
            lignes = [(p.pk, p.nom, p.email) for p in qs.order_by('nom')[:30]]
        elif type_contrat == 'ong':
            qs = OrganisationModel.objects.all()
            if q:
                qs = qs.filter(nom__icontains=q)
            lignes = [(o.pk, o.nom, o.contact_email) for o in qs.order_by('nom')[:30]]
        else:
            return Response({'type': ['Type de contrat inconnu.']}, status=status.HTTP_400_BAD_REQUEST)
        champ = {'hote': 'hote_id', 'hotel': 'hote_id', 'chauffeur': 'chauffeur_id', 'loueur': 'loueur_id', 'ong': 'organisation_id'}[type_contrat]
        statuts = dict(ContratModel.objects.filter(**{f"{champ}__in": [pk for pk, _, _ in lignes]}).exclude(statut='annule')
                       .values_list(champ, 'statut'))
        return Response([{'id': str(pk), 'nom': nom, 'email': email or '', 'contrat': statuts.get(pk)} for pk, nom, email in lignes])


class ContratAdminActionView(APIView):
    """POST renvoyer | annuler {motif}."""
    permission_classes = [EstAdministrateur]

    def post(self, request, pk, action):
        contrat = ContratModel.objects.filter(pk=pk).first()
        if not contrat:
            return Response({'detail': 'Contrat introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            if action == 'renvoyer':
                contrat = services.renvoyer(contrat)
            elif action == 'annuler':
                contrat = services.annuler(contrat, str(request.data.get('motif', '')))
            else:
                return Response({'detail': 'Action inconnue.'}, status=status.HTTP_404_NOT_FOUND)
        except services.ContratErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        journaliser('backoffice_modification', request, utilisateur=request.user, objet='contrat', id=str(contrat.pk), champs=[action])
        return Response(_admin(contrat))


class ContratAdminPdfView(APIView):
    permission_classes = [EstAdministrateur]

    def get(self, request, pk):
        contrat = ContratModel.objects.filter(pk=pk).first()
        if not contrat:
            return Response({'detail': 'Contrat introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return _pdf(contrat)


def _modele(m: ModeleContratModel) -> dict:
    return {'type': m.type, 'type_libelle': m.get_type_display(), 'titre': m.titre, 'corps': m.corps,
            'version': m.version, 'modifie_le': m.modifie_le}


class ModelesAdminView(APIView):
    permission_classes = [EstAdministrateur]

    def get(self, request):
        return Response({'modeles': [_modele(m) for m in ModeleContratModel.objects.all()], 'variables': services.VARIABLES})


class ModeleAdminView(APIView):
    """PUT {titre, corps}: new version of the template (contracts already issued keep their text)."""
    permission_classes = [EstAdministrateur]

    def put(self, request, type_contrat):
        modele = ModeleContratModel.objects.filter(type=type_contrat).first()
        if not modele:
            return Response({'detail': 'Modèle introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        titre, corps = str(request.data.get('titre', '')).strip(), str(request.data.get('corps', '')).strip()
        erreurs = {}
        if not 5 <= len(titre) <= 150:
            erreurs['titre'] = ['Entre 5 et 150 caractères.']
        if len(corps) < 100:
            erreurs['corps'] = ['Le texte du contrat est trop court.']
        elif len(corps) > 60_000:
            erreurs['corps'] = ['Le texte du contrat est trop long.']
        inconnues = sorted({v for v in services._VARIABLE.findall(corps) if v not in services.VARIABLES})
        if inconnues:
            erreurs['corps'] = [f"Variable inconnue : {', '.join('{{ ' + v + ' }}' for v in inconnues)}."]
        if erreurs:
            return Response(erreurs, status=status.HTTP_400_BAD_REQUEST)
        if (titre, corps) != (modele.titre, modele.corps):
            modele.titre, modele.corps, modele.version, modele.modifie_par = titre, corps, modele.version + 1, request.user
            modele.save()
            journaliser('backoffice_modification', request, utilisateur=request.user, objet='modele_contrat', id=modele.type,
                        champs=['titre', 'corps'], version=modele.version)
        return Response(_modele(modele))


class PreinscriptionView(APIView):
    """Pre-launch pre-registration of the connected host.

    GET : {requise, acceptee, version, texte} in the site's language (Accept-Language).
    POST {accepte: true, version, langue} : records the acceptance with its date, IP address and browser.
    """
    permission_classes = [EstHote]

    def get_throttles(self):
        return [LimiteSignature()] if self.request.method == 'POST' else []

    def get(self, request):
        langue = preinscription.langue_de(request.headers.get('Accept-Language', ''))
        return Response({
            'requise': prelancement.actif(), 'acceptee': preinscription.acceptee(request.user),
            'version': preinscription.VERSION, 'langue': langue, 'texte': preinscription.TEXTES[langue],
        })

    def post(self, request):
        if request.data.get('accepte') is not True:
            return Response({'accepte': ["Cochez la case pour accepter la pré-inscription."]}, status=status.HTTP_400_BAD_REQUEST)
        # The host accepts the text they read: a newer version must be read first
        if request.data.get('version') != preinscription.VERSION:
            return Response({'detail': "Le texte de pré-inscription a changé : relisez-le avant de l'accepter.",
                             'code': 'version_perimee'}, status=status.HTTP_409_CONFLICT)
        langue = request.data.get('langue')
        if langue not in preinscription.LANGUES:
            return Response({'langue': ['Langue inconnue.']}, status=status.HTTP_400_BAD_REQUEST)
        preinscription.accepter(request.user, langue=langue, ip=ip_client(request),
                                user_agent=request.META.get('HTTP_USER_AGENT', ''))
        return Response({'acceptee': True}, status=status.HTTP_201_CREATED)
