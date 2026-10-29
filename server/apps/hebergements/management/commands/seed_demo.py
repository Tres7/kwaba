import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.hebergements.models import HebergementModel

U = "https://images.unsplash.com/"
Q = "?q=80&w=1200&auto=format&fit=crop"

INTERIORS = [
    f"{U}photo-1618221195710-dd6b41faaea6{Q}",
    f"{U}photo-1582719478250-c89cae4dc85b{Q}",
    f"{U}photo-1584622650111-993a426fbf0a{Q}",
    f"{U}photo-1512918728675-ed5a9ecdebfd{Q}",
]

DEMO = [
    ("Villa Hibiscus", "villa", "Assinie", "Bord de lagune, Assinie-Mafia", 125000, 4.8, 64, 8,
     "photo-1613490493576-7fde63acd811", ["piscine", "wifi", "clim", "parking", "jardin"],
     "Villa pieds dans l'eau entre lagune et océan. Quatre chambres climatisées, grande terrasse en bois et piscine privée. Idéale pour les familles et les groupes d'amis qui veulent profiter de la plage d'Assinie au calme."),
    ("Riad Jasmin", "hotel", "Marrakech", "Médina, Derb Sidi Bouloukat", 85000, 4.9, 212, 4,
     "photo-1539020140153-e479b8c22e70", ["wifi", "clim", "spa"],
     "Riad traditionnel au cœur de la médina, à cinq minutes à pied de la place Jemaa el-Fna. Patio fleuri, hammam et petit-déjeuner marocain servi sur le toit-terrasse."),
    ("Loft Plateau", "appartement", "Dakar", "Plateau, rue Carnot", 60000, 4.7, 98, 3,
     "photo-1502672260266-1c1e55240c5f", ["wifi", "clim", "cuisine"],
     "Loft lumineux en plein centre de Dakar, proche des restaurants et du marché Kermel. Cuisine équipée, espace de travail et connexion fibre."),
    ("Suite Océan", "hotel", "Dakar", "Les Almadies", 90000, 4.8, 143, 2,
     "photo-1499793983690-e29da59ef1c2", ["piscine", "wifi", "clim", "spa", "gym"],
     "Suite avec vue sur l'Atlantique à la pointe des Almadies. Accès à la piscine à débordement, au spa et à la salle de sport de l'hôtel."),
    ("Résidence Lagune", "appartement", "Lomé", "Bè Kpota, près de la lagune", 35000, 4.6, 51, 4,
     "photo-1522708323590-d24dbb6b0267", ["wifi", "clim", "cuisine", "parking"],
     "Appartement deux chambres entièrement meublé, dans un quartier calme de Lomé. À dix minutes de la plage et du grand marché."),
    ("Hôtel Sarakawa View", "hotel", "Lomé", "Boulevard du Mono", 55000, 4.5, 187, 2,
     "photo-1566073771259-6a8506099945", ["piscine", "wifi", "clim", "parking", "gym"],
     "Chambre supérieure face à la mer sur le boulevard du Mono. Piscine, restaurant et navette vers l'aéroport."),
    ("Villa Cocody", "villa", "Abidjan", "Cocody, Riviera 3", 110000, 4.7, 76, 6,
     "photo-1600596542815-ffad4c1539a9", ["piscine", "wifi", "clim", "parking", "jardin", "cuisine"],
     "Villa moderne avec jardin tropical dans le quartier résidentiel de Cocody. Personnel de maison disponible sur demande."),
    ("Studio Plateau Business", "appartement", "Abidjan", "Plateau, avenue Chardy", 40000, 4.4, 39, 2,
     "photo-1560448204-e02f11c3d0e2", ["wifi", "clim", "cuisine"],
     "Studio fonctionnel au cœur du quartier d'affaires, parfait pour un déplacement professionnel."),
    ("Auberge Ganvié", "auberge", "Cotonou", "Fidjrossè plage", 25000, 4.5, 58, 3,
     "photo-1520250497591-112f2f40a3f4", ["wifi", "jardin"],
     "Auberge conviviale à deux pas de la plage de Fidjrossè. Excursions organisées vers la cité lacustre de Ganvié."),
    ("Maison de Pierre", "villa", "Kigali", "Kiyovu", 55000, 4.9, 121, 5,
     "photo-1568605114967-8130f3a36994", ["wifi", "parking", "jardin", "cuisine"],
     "Maison en pierre volcanique avec vue sur les collines de Kigali. Calme absolu, cheminée et grand jardin."),
    ("Bungalow Lagon", "villa", "Zanzibar", "Paje, côte est", 180000, 4.9, 167, 4,
     "photo-1590523277543-a94d2e4eb00b", ["piscine", "wifi", "clim", "spa"],
     "Bungalow sur pilotis face au lagon turquoise de Paje. Petit-déjeuner inclus et accès direct à la plage."),
    ("Accra Skyline Apartment", "appartement", "Accra", "Airport Residential Area", 70000, 4.6, 88, 4,
     "photo-1545324418-cc1a3fa10c00", ["piscine", "wifi", "clim", "gym", "parking"],
     "Appartement haut de gamme au 12e étage, vue panoramique sur Accra. Piscine sur le toit et sécurité 24h/24."),
]


# Typical details per listing type (area, bedrooms, beds, breakfast)
DETAILS = {
    'villa': {'surface_m2': 180, 'chambres': 4, 'salles_de_bain': 3, 'lits_doubles': 3, 'lits_simples': 2,
              'petit_dejeuner': 'option', 'petit_dejeuner_prix': 5000},
    'appartement': {'surface_m2': 75, 'chambres': 2, 'salles_de_bain': 1, 'lits_doubles': 1, 'lits_simples': 1,
                    'petit_dejeuner': 'non'},
    'hotel': {'surface_m2': 32, 'chambres': 1, 'salles_de_bain': 1, 'lits_doubles': 1, 'petit_dejeuner': 'inclus'},
    'auberge': {'surface_m2': 28, 'chambres': 1, 'salles_de_bain': 1, 'lits_simples': 2, 'petit_dejeuner': 'inclus'},
}
HORAIRES = {'arrivee_a_partir': '14:00', 'depart_avant': '11:00'}


class Command(BaseCommand):
    help = "Crée un hôte de démonstration et des hébergements réalistes (idempotent)."

    def handle(self, *args, **options):
        email = os.getenv('DEMO_HOST_EMAIL', 'hote.demo@kwa-ba.com')
        password = os.getenv('DEMO_HOST_PASSWORD', 'Kwa-Ba2026!')

        host, created = get_user_model().objects.get_or_create(
            email=email,
            defaults={'first_name': 'Kossi', 'last_name': 'Mensah', 'role': 'hote', 'is_verified': True},
        )
        if created:
            host.set_password(password)
            host.save()
            self.stdout.write(f"Hôte démo créé : {email} / {password}")

        added = 0
        for name, type_, city, location, price, _rating, _reviews, guests, photo, amenities, desc in DEMO:
            cover = f"{U}{photo}{Q}"
            _, was_created = HebergementModel.objects.get_or_create(
                name=name,
                host=host,
                defaults={
                    'type': type_, 'city': city, 'location': location,
                    'price_per_night': price,
                    'max_guests': guests, 'image_url': cover,
                    'images': [cover, *INTERIORS], 'amenities': amenities,
                    'description': desc, **DETAILS[type_], **HORAIRES,
                },
            )
            added += was_created

        self.stdout.write(self.style.SUCCESS(f"{added} hébergement(s) ajouté(s), {len(DEMO)} au total."))
