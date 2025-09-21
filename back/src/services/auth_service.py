"""
Authentication service for user registration and login
"""

import os
import uuid
from typing import Optional
from datetime import datetime
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, HashingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_
from pydantic import ValidationError

from ..models.auth import (
    RegisterRequest,
    LoginRequest,
    RegisterResponse,
    AuthResponse,
    UserResponse,
    MerchantResponse,
    CurrentPrincipal,
    UserRole,
)
from ..utils.jwt import create_access_token, JWTError

# Password hashing configuration
PASSWORD_PEPPER = os.getenv("PASSWORD_PEPPER", "")
ph = PasswordHasher()


class AuthError(Exception):
    """Authentication related errors"""

    pass


class AuthService:
    """Authentication service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _hash_password(self, password: str) -> str:
        """Hash password using Argon2id with optional pepper"""
        try:
            peppered_password = password + PASSWORD_PEPPER
            return ph.hash(peppered_password)
        except HashingError as e:
            raise AuthError(f"Password hashing failed: {str(e)}")

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            peppered_password = password + PASSWORD_PEPPER
            ph.verify(hashed, peppered_password)
            return True
        except VerifyMismatchError:
            return False
        except Exception as e:
            raise AuthError(f"Password verification failed: {str(e)}")

    async def register(self, request: RegisterRequest) -> RegisterResponse:
        """
        Register new user and create merchant

        Args:
            request: Registration request data

        Returns:
            RegisterResponse with token and user/merchant info

        Raises:
            AuthError: If registration fails
        """
        try:
            # Note: Email uniqueness check is now handled by the bootstrap function

            # Hash password
            password_hash = self._hash_password(request.password)

            # Call bootstrap function that bypasses RLS
            result = await self.db.execute(
                text(
                    """
                    SELECT out_merchant_id, out_user_id
                    FROM public.register_merchant_and_admin(
                        :p_name,
                        :p_email,
                        :p_password_hash,
                        :p_business_name,
                        :p_whatsapp
                    )
                """
                ),
                {
                    "p_name": request.name,
                    "p_email": request.email,
                    "p_password_hash": password_hash,
                    "p_business_name": request.business_name,
                    "p_whatsapp": request.whatsapp_phone_e164,
                },
            )
            row = result.fetchone()

            if not row:
                raise AuthError("Bootstrap function returned no results")

            # Use the IDs returned by the function
            merchant_id = str(row.out_merchant_id)
            user_id = str(row.out_user_id)

            # Commit the transaction
            await self.db.commit()

            # Create JWT token
            token = create_access_token(
                user_id=uuid.UUID(user_id),
                email=request.email,
                merchant_id=uuid.UUID(merchant_id),
                role=UserRole.ADMIN.value,
            )

            # Build response
            user_response = UserResponse(
                id=uuid.UUID(user_id),
                name=request.name,
                email=request.email,
                role=UserRole.ADMIN,
                merchant_id=uuid.UUID(merchant_id),
            )

            merchant_response = MerchantResponse(
                id=uuid.UUID(merchant_id),
                name=request.business_name,
                whatsapp_phone_e164=request.whatsapp_phone_e164,
            )

            return RegisterResponse(
                token=token, user=user_response, merchant=merchant_response
            )

        except ValidationError as e:
            raise AuthError(f"Validation error: {str(e)}")
        except AuthError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise AuthError(f"Registration failed: {str(e)}")

    async def login(self, request: LoginRequest) -> AuthResponse:
        """
        Authenticate user and return token

        Args:
            request: Login request data

        Returns:
            AuthResponse with token and user info

        Raises:
            AuthError: If authentication fails
        """
        try:
            # Get user with password hash using login lookup function (bypasses RLS)
            result = await self.db.execute(
                text(
                    """
                    SELECT out_user_id, out_merchant_id, out_name, out_email, out_password_hash, out_role
                    FROM public.lookup_user_for_login(:email)
                """
                ),
                {"email": request.email},
            )
            user_row = result.fetchone()

            if not user_row:
                raise AuthError("Invalid credentials")

            # Verify password
            if not self._verify_password(request.password, user_row.out_password_hash):
                raise AuthError("Invalid credentials")

            # Create JWT token
            token = create_access_token(
                user_id=user_row.out_user_id,
                email=user_row.out_email,
                merchant_id=user_row.out_merchant_id,
                role=user_row.out_role,
            )

            # Skip last login update for now to avoid RLS issues
            # await self.db.execute(
            #     text("UPDATE users SET last_login_at = NOW() WHERE id = :user_id"),
            #     {"user_id": str(user_row.out_user_id)}
            # )
            # await self.db.commit()

            # Build response
            user_response = UserResponse(
                id=user_row.out_user_id,
                name=user_row.out_name,
                email=user_row.out_email,
                role=UserRole(user_row.out_role),
                merchant_id=user_row.out_merchant_id,
            )

            return AuthResponse(token=token, user=user_response)

        except AuthError:
            raise
        except Exception as e:
            raise AuthError(f"Login failed: {str(e)}")

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[CurrentPrincipal]:
        """
        Get user by ID for authentication

        Args:
            user_id: User UUID

        Returns:
            CurrentPrincipal or None if not found
        """
        try:
            result = await self.db.execute(
                text(
                    """
                    SELECT id, merchant_id, name, email, role
                    FROM users 
                    WHERE id = :user_id
                """
                ),
                {"user_id": str(user_id)},
            )
            user_row = result.fetchone()

            if not user_row:
                return None

            return CurrentPrincipal(
                user_id=user_row.id,
                merchant_id=user_row.merchant_id,
                role=UserRole(user_row.role),
                email=user_row.email,
            )

        except Exception as e:
            raise AuthError(f"Failed to get user: {str(e)}")
