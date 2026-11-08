# Guide d'installation de l'environnement de developpement

## Pre-requis

- **Docker Desktop** installe et demarre
- **Git** configure

## Etape 1 : Cloner et configurer

```bash
git clone https://github.com/kwa-ba/kwaba.git
cd kwaba
cp .env.example .env
```

Editez `.env` avec vos propres valeurs :
```env
POSTGRES_DB=kwaba
POSTGRES_USER=votre_username
POSTGRES_PASSWORD=votre_password

PGADMIN_EMAIL=votre_email@example.com
PGADMIN_PASSWORD=votre_password

DJANGO_SECRET_KEY=votre-cle-secrete
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,backend
```

## Etape 2 : Lancer les services

```bash
docker compose up --build
```

Cela va :
- Telecharger les images PostgreSQL et pgAdmin
- Construire les images backend (Django) et frontend (Next.js)
- Demarrer tous les services, dont deux processus en arrière-plan :
  - `consumer` : envoie les emails à partir des événements RabbitMQ
  - `messaging-relay` : publie les notifications de la messagerie (voir [modules/messaging.md](modules/messaging.md))

## Etape 3 : Initialiser la base de donnees

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

`migrate` crée aussi la table de cache `django_cache` utilisée par les limites de débit (throttles) de la messagerie : aucune commande supplémentaire n'est nécessaire.

Sur un environnement existant, après avoir récupéré le module messagerie : lancer `migrate`, puis `docker compose up -d` pour démarrer le nouveau service `messaging-relay` et redémarrer `consumer` (qui doit écouter le nouvel événement).

## Acces aux services

| Service        | URL                          |
|----------------|------------------------------|
| Frontend       | http://localhost:3000         |
| Backend API    | http://localhost:8000         |
| Admin Django   | http://localhost:8000/admin   |
| pgAdmin        | http://localhost:5051         |

## Configuration pgAdmin

1. Ouvrir http://localhost:5051
2. Se connecter avec les identifiants du `.env`
3. Ajouter un nouveau serveur :
   - **Host** : `db` (nom du service Docker)
   - **Port** : `5432` (port interne du container)
   - **Username** : valeur de `POSTGRES_USER`
   - **Password** : valeur de `POSTGRES_PASSWORD`

![img.png](img.png)
![img_1.png](img_1.png)

## Commandes utiles

```bash
# Arreter les services
docker compose down

# Voir les logs d'un service
docker compose logs -f backend

# Reinitialiser la base de donnees
docker compose down -v   # supprime le volume
docker compose up --build
docker compose exec backend python manage.py migrate
```

## RabbitMQ : dead-letter queue des notifications

Les messages que le consumer n'arrive pas à traiter sont envoyés dans `notifications.events.dlq` au lieu d'être perdus (voir ADR-014).

```bash
# Nombre de messages dans chaque file
docker compose exec rabbitmq rabbitmqctl list_queues name messages
```

Les messages de la DLQ sont consultables et rejouables depuis l'interface RabbitMQ : http://localhost:15672 (identifiants `RABBITMQ_DEFAULT_USER` / `RABBITMQ_DEFAULT_PASS` du `.env`), onglet *Queues* > `notifications.events.dlq`.

### Migration unique sur un environnement existant

Si le consumer s'arrête au démarrage avec le message `La file 'notifications.events' existe déjà sans dead-letter exchange`, la file a été créée par une ancienne version. Vérifier qu'elle est vide, la supprimer, puis relancer le consumer qui la recrée :

```bash
docker compose exec rabbitmq rabbitmqctl list_queues name messages   # notifications.events doit être à 0
docker compose exec rabbitmq rabbitmqctl delete_queue notifications.events
docker compose restart consumer
```
