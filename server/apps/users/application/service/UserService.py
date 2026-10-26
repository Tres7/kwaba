import logging
import uuid

from django.contrib.auth.hashers import make_password

from apps.users.domain.entities.User import User, UserRole
from apps.users.domain.repositories.UserRepository import UserRepository
from apps.users.domain.exceptions import (
    UserAlreadyExistsException,
    UserNotFoundException
)
from datetime import timedelta
from django.utils import timezone
from apps.users.infrastructure.persistence.models import UserModel, VerificationCode, hacher_code

from apps.users.application.dto.dto import (
    GoogleAuthDTO,
    RegisterDTO,
    UpdateProfileDTO,
    UserResponseDTO
)
from apps.users.application.events.UserRegistered import UserRegistered
from apps.users.application.events.WelcomeEmailRequested import WelcomeEmailRequested
from apps.users.application.ports import EventPublisher
from apps.users.domain.value_objects import Email, PasswordHash, PhoneNumber

logger = logging.getLogger(__name__)


class UserService:

    def __init__(self, user_repository: UserRepository):
        self._repository = user_repository

    def register(self, dto: RegisterDTO, event_bus: EventPublisher, code: str) -> UserResponseDTO:
        if self._repository.exists_by_email(dto.email):
            raise UserAlreadyExistsException(dto.email)

        if dto.phone and self._repository.exists_by_phone(dto.phone):
            raise UserAlreadyExistsException(dto.phone)

        user = User(
            email=dto.email,
            first_name=dto.first_name,
            last_name=dto.last_name,
            password_hash=dto.password_hash,
            role=dto.role,
            phone=PhoneNumber.of(dto.phone) if isinstance(dto.phone, str) else dto.phone,
        )

        saved_user = self._repository.save(user)
        self.store_verification_code(saved_user.id, code)

        try:
            event_bus.publish(UserRegistered(
                event='users.email_verification_requested',
                user_id=str(saved_user.id),
                email=str(saved_user.email),
                first_name=saved_user.first_name,
                code=code,
            ))
        except Exception:
            # RabbitMQ indisponible : l'inscription reste valide, l'utilisateur peut redemander un code
            logger.exception(
                "Publication de users.email_verification_requested impossible (user_id=%s)",
                saved_user.id,
            )

        return UserResponseDTO.from_entity(saved_user)

    def get_by_id(self, user_id: uuid.UUID) -> UserResponseDTO:
        user = self._repository.find_by_id(user_id)
        if not user:
            raise UserNotFoundException(str(user_id))
        return UserResponseDTO.from_entity(user)

    def update_profile(self, user_id: uuid.UUID, dto: UpdateProfileDTO) -> UserResponseDTO:
        user = self._repository.find_by_id(user_id)
        if not user:
            raise UserNotFoundException(str(user_id))

        if dto.first_name:
            user.first_name = dto.first_name
        if dto.last_name:
            user.last_name = dto.last_name
        if dto.phone:
            user.phone = dto.phone
        if dto.avatar_url:
            user.avatar_url = dto.avatar_url

        updated_user = self._repository.update(user)
        return UserResponseDTO.from_entity(updated_user)

    def verify_account(self, user_id: uuid.UUID) -> None:
        user = self._repository.find_by_id(user_id)
        if not user:
            raise UserNotFoundException(str(user_id))
        user.verify()
        self._repository.update(user)

    def become_host(self, user_id: uuid.UUID) -> UserResponseDTO:
        user = self._repository.find_by_id(user_id)
        if not user:
            raise UserNotFoundException(str(user_id))
        if user.role == UserRole.VOYAGEUR:
            user.change_role(UserRole.HOTE)
            user = self._repository.update(user)
        return UserResponseDTO.from_entity(user)

    def deactivate(self, user_id: uuid.UUID) -> None:
        user = self._repository.find_by_id(user_id)
        if not user:
            raise UserNotFoundException(str(user_id))
        user.deactivate()
        self._repository.update(user)

    def find_for_authentication(self, email: str) -> User:
        """Returns the full entity with password_hash for authentication."""
        user = self._repository.find_by_email(email)
        if not user:
            raise UserNotFoundException(email)
        return user

    def google_authenticate(self, dto: GoogleAuthDTO, verifier) -> UserResponseDTO:
        info = verifier.verify(dto.id_token)

        if not info.email_verified:
            raise ValueError("L'adresse email Google n'est pas vérifiée.")

        user = self._repository.find_by_google_id(info.google_id)

        if not user:
            user = self._repository.find_by_email(info.email)
            if user:
                user.google_id = info.google_id
                user.is_verified = True
                if info.avatar_url and not user.avatar_url:
                    user.avatar_url = info.avatar_url
                user = self._repository.update(user)
            else:
                user = User(
                    email=Email(info.email),
                    first_name=info.first_name,
                    last_name=info.last_name,
                    password_hash=PasswordHash(make_password(None)),
                    role=UserRole.VOYAGEUR,
                    is_verified=True,
                    avatar_url=info.avatar_url,
                    google_id=info.google_id,
                )
                user = self._repository.save(user)

        return UserResponseDTO.from_entity(user)
    

    def store_verification_code(self, user_id, code: str) -> None:
        VerificationCode.objects.filter(user_id=user_id).delete()
        VerificationCode.objects.create(
            user_id=user_id,
            code=hacher_code(user_id, code),
            expires_at=timezone.now() + timedelta(minutes=10),
        )

    def verify_email(self, email: str, code: str, event_bus: EventPublisher) -> uuid.UUID:
        try:
            user_model = UserModel.objects.get(email__iexact=email.strip())
        except UserModel.DoesNotExist:
            raise UserNotFoundException(email)

        if user_model.is_verified:
            raise ValueError("Compte déjà vérifié.")

        vc = VerificationCode.objects.filter(user=user_model, expires_at__gt=timezone.now()).order_by('-expires_at').first()
        if not vc or not vc.correspond(code):
            raise ValueError("Code invalide ou expiré.")

        user_model.is_verified = True
        user_model.save(update_fields=["is_verified"])
        vc.delete()
        try:
            event_bus.publish(WelcomeEmailRequested(
                event="users.welcome_email_requested",
                user_id=str(user_model.id),
                email=user_model.email,
                first_name=user_model.first_name,
            ))
        except Exception:
            logger.exception(
                "Publication de users.welcome_email_requested impossible (user_id=%s)",
                user_model.id,
            )

        return user_model.id
