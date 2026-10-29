"""Unit types (TypeLogementModel): one default type per establishment, migration of the existing data, bookings."""
import importlib
from datetime import timedelta
from decimal import Decimal

import pytest
from django.apps import apps as registre
from django.db import IntegrityError
from django.utils import timezone

from apps.hebergements.models import HebergementModel, TypeLogementModel
from apps.reservations.models import ReservationModel

HEBERGEMENTS = '/api/v1/hebergements/'
RESERVATIONS = '/api/v1/reservations/'


def _annonce(**extra):
    return {'name': 'Hôtel du Golfe', 'city': 'Lomé', 'type': 'hotel', 'price_per_night': 30000, 'max_guests': 2,
            'surface_m2': 25, 'chambres': 1, 'lits_doubles': 1, 'lits_simples': 0, 'petit_dejeuner': 'non', **extra}


class TestDefaultType:
    def test_a_new_listing_gets_one_unit_of_its_own_price(self, client_for, make_user):
        reponse = client_for(make_user(role='hote')).post(HEBERGEMENTS, _annonce(), format='json')
        assert reponse.status_code == 201
        (seul,) = TypeLogementModel.objects.filter(hebergement_id=reponse.data['id'])
        assert (seul.nom, seul.quantite, seul.capacite, seul.prix_nuit) == ('Chambre', 1, 2, Decimal('30000'))

    @pytest.mark.parametrize('type_etablissement, nom', [('villa', 'Logement entier'), ('maison', 'Logement entier'),
                                                         ('residence', 'Appartement'), ('appartement', 'Appartement entier')])
    def test_default_name_follows_the_kind_of_establishment(self, client_for, make_user, type_etablissement, nom):
        reponse = client_for(make_user(role='hote')).post(HEBERGEMENTS, _annonce(type=type_etablissement), format='json')
        assert TypeLogementModel.objects.get(hebergement_id=reponse.data['id']).nom == nom

    def test_editing_the_listing_keeps_its_single_type_in_line(self, client_for, make_hebergement):
        annonce = make_hebergement(price_per_night=20000, max_guests=3)
        client_for(annonce.host).patch(f'{HEBERGEMENTS}{annonce.id}/', {'price_per_night': 26000, 'max_guests': 5}, format='json')
        seul = annonce.types.get()
        assert (seul.prix_nuit, seul.capacite, seul.quantite) == (Decimal('26000'), 5, 1)

    def test_a_type_with_several_units_is_not_overwritten(self, client_for, make_hebergement):
        annonce = make_hebergement(price_per_night=20000)
        annonce.types.update(quantite=12)
        TypeLogementModel.objects.create(hebergement=annonce, nom='Suite', capacite=4, prix_nuit=60000, quantite=2)
        client_for(annonce.host).patch(f'{HEBERGEMENTS}{annonce.id}/', {'price_per_night': 26000}, format='json')
        assert sorted(annonce.types.values_list('prix_nuit', flat=True)) == [Decimal('20000'), Decimal('60000')]

    def test_database_rejects_an_empty_stock(self, make_hebergement):
        with pytest.raises(IntegrityError):
            TypeLogementModel.objects.create(hebergement=make_hebergement(), nom='Vide', prix_nuit=1000, quantite=0)


def test_a_booking_points_to_the_unit_type(client_for, make_user, make_hebergement, settings):
    settings.PAIEMENT_HORS_LIGNE = True
    annonce = make_hebergement()
    arrivee = timezone.localdate() + timedelta(days=10)
    reponse = client_for(make_user()).post(RESERVATIONS, {
        'hebergement': str(annonce.id), 'check_in': arrivee.isoformat(),
        'check_out': (arrivee + timedelta(days=2)).isoformat(), 'guests_count': 2}, format='json')
    assert reponse.status_code == 201
    reservation = ReservationModel.objects.get(pk=reponse.data['id'])
    assert (reservation.type_logement, reservation.nb_unites) == (annonce.types.get(), 1)


def test_deleting_an_establishment_with_bookings_keeps_its_types(client_for, make_hebergement, make_reservation):
    annonce = make_hebergement()
    make_reservation(annonce, status='cancelled')
    ReservationModel.objects.update(type_logement=annonce.types.get())
    assert client_for(annonce.host).delete(f'{HEBERGEMENTS}{annonce.id}/').status_code == 204
    assert TypeLogementModel.objects.filter(hebergement=annonce).exists()


class TestDataMigration:
    """The production data: establishments without a type and bookings without a type."""

    def test_existing_listings_and_bookings_get_their_default_type(self, make_user, make_hebergement, make_reservation):
        annonce = make_hebergement(type='villa', price_per_night=40000, max_guests=6)
        reservation = make_reservation(annonce)
        TypeLogementModel.objects.all().delete()  # as before the migration
        HebergementModel.objects.filter(pk=annonce.pk).update(type='hotel')

        importlib.import_module('apps.hebergements.migrations.0010_types_par_defaut').creer_types_par_defaut(registre, None)
        importlib.import_module('apps.reservations.migrations.0006_rattacher_type_logement').rattacher(registre, None)

        seul = annonce.types.get()
        assert (seul.nom, seul.quantite, seul.capacite, seul.prix_nuit) == ('Chambre', 1, 6, Decimal('40000'))
        reservation.refresh_from_db()
        assert reservation.type_logement == seul

    def test_running_it_twice_creates_nothing_more(self, make_hebergement):
        make_hebergement()
        importlib.import_module('apps.hebergements.migrations.0010_types_par_defaut').creer_types_par_defaut(registre, None)
        assert TypeLogementModel.objects.count() == 1


def test_the_listing_page_shows_its_unit_types_and_lists_do_not(api_client, make_hebergement):
    annonce = make_hebergement(type='hotel', price_per_night=30000, max_guests=2)
    TypeLogementModel.objects.create(hebergement=annonce, nom='Suite', capacite=4, prix_nuit=80000, quantite=2, ordre=1)
    TypeLogementModel.objects.create(hebergement=annonce, nom='Fermée', capacite=2, prix_nuit=9000, quantite=1, actif=False)
    types = api_client.get(f'{HEBERGEMENTS}{annonce.id}/').data['types']
    assert [(t['nom'], t['quantite'], t['prix_nuit']) for t in types] == [('Chambre', 1, 30000.0), ('Suite', 2, 80000.0)]
    assert {h['types'] for h in api_client.get(HEBERGEMENTS).data['results']} == {None}
