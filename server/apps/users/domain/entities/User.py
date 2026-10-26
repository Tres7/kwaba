from dataclasses import dataclass, field
import datetime
from enum import Enum
from typing import Optional
import uuid

from apps.users.domain.value_objects import Email, PasswordHash, PhoneNumber


class UserRole(Enum):
    VOYAGEUR = 'voyageur'
    HOTE = 'hote'
    ADMIN = 'admin'
    AGENT = 'agent'

@dataclass
class User:
    email: Email
    first_name: str
    last_name: str
    password_hash: PasswordHash
    role: UserRole
    is_verified: bool = False
    is_active: bool = True
    phone: Optional[PhoneNumber] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def is_host(self) -> bool:
        return self.role == UserRole.HOTE

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def verify(self) -> None:
        """Validates the account after email confirmation"""
        self.is_verified = True
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

    def change_role(self, new_role: UserRole) -> None:
        self.role = new_role
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)
