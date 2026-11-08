# infrastructure/persistence/user_repository.py
import uuid
from collections.abc import Iterable
from typing import Optional

from apps.users.domain.entities.User import User, UserRole
from apps.users.domain.repositories.UserRepository import UserRepository
from apps.users.domain.exceptions import UserNotFoundException
from apps.users.infrastructure.persistence.models import UserModel
from apps.users.domain.value_objects import Email, PasswordHash, PhoneNumber


class DjangoUserRepository(UserRepository):

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            email=Email(model.email),
            first_name=model.first_name,
            last_name=model.last_name,
            password_hash=PasswordHash(model.password),
            phone=PhoneNumber.of(model.phone),
            avatar_url=model.avatar.url if model.avatar else None,
            google_id=model.google_id,
            role=UserRole(model.role),
            is_verified=model.is_verified,
            is_active=model.is_active,
            created_at=model.date_joined,
            updated_at=model.last_login,
        )

    def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        try:
            model = UserModel.objects.get(id=user_id)
            return self._to_entity(model)
        except UserModel.DoesNotExist:
            return None

    def find_by_email(self, email: str) -> Optional[User]:
        try:
            model = UserModel.objects.get(email__iexact=email.strip())
            return self._to_entity(model)
        except UserModel.DoesNotExist:
            return None

    def find_by_phone(self, phone: str) -> Optional[User]:
        try:
            model = UserModel.objects.get(phone=phone)
            return self._to_entity(model)
        except UserModel.DoesNotExist:
            return None

    def save(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=str(user.email).strip().lower(),
            google_id=user.google_id,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=PhoneNumber.to_str(user.phone),
            role=user.role.value,
            is_verified=user.is_verified,
            is_active=user.is_active,
        )
        model.password = str(user.password_hash)
        model.save()
        return self._to_entity(model)

    def update(self, user: User, champs: Iterable[str] | None = None) -> User:
        try:
            model = UserModel.objects.get(id=user.id)
        except UserModel.DoesNotExist:
            raise UserNotFoundException(f"Utilisateur {user.id} introuvable.")

        valeurs = {
            'email': str(user.email),
            'google_id': user.google_id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': PhoneNumber.to_str(user.phone),
            'role': user.role.value,
            'is_verified': user.is_verified,
            'is_active': user.is_active,
        }
        champs = list(valeurs) if champs is None else list(champs)
        for champ in champs:
            setattr(model, champ, valeurs[champ])
        model.save(update_fields=champs)
        return self._to_entity(model)

    def oublier_mot_de_passe(self, user_id: uuid.UUID) -> None:
        from apps.users.api import revoquer_jetons  # local import: the users API loads this module's models

        model = UserModel.objects.get(id=user_id)
        model.set_unusable_password()  # access tokens issued before are refused too (CHECK_REVOKE_TOKEN)
        model.save(update_fields=['password'])
        revoquer_jetons(user_id)
    
    def find_by_google_id(self, google_id: str) -> Optional[User]:
        try:
            model = UserModel.objects.get(google_id=google_id)
            return self._to_entity(model)
        except UserModel.DoesNotExist:
            return None


    def delete(self, user_id: uuid.UUID) -> None:
        try:
            model = UserModel.objects.get(id=user_id)
            model.delete()
        except UserModel.DoesNotExist:
            raise UserNotFoundException(f"Utilisateur {user_id} introuvable.")

    def exists_by_email(self, email: str) -> bool:
        return UserModel.objects.filter(email__iexact=str(email).strip()).exists()

    def exists_by_phone(self, phone: str) -> bool:
        return UserModel.objects.filter(phone=phone).exists()
