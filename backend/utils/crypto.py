"""Crypto utilities for encrypting/decrypting sensitive data."""

from __future__ import annotations

import base64
import logging
import os

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class CryptoService:
    """Fernet-based symmetric encryption service for sensitive data."""

    def __init__(self, key: str):
        """
        Initialize with a Fernet key.

        Args:
            key: Base64-encoded Fernet key (44 characters)
        """
        if not key:
            raise ValueError("Encryption key cannot be empty")
        try:
            self.fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}") from e

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded ciphertext string
        """
        if not plaintext:
            return ""
        encrypted = self.fernet.encrypt(plaintext.encode("utf-8"))
        return encrypted.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Base64-encoded ciphertext

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""
        try:
            decrypted = self.fernet.decrypt(ciphertext.encode("utf-8"))
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error("Failed to decrypt: %s", e)
            return ""

    @staticmethod
    def mask_token(token: str) -> str:
        """
        Create a masked version of a token for display.

        Examples:
            ghp_xxxxxxxxxxxxxxxxxxxx -> ghp_****xxxx
            sk-xxxxxxxxxxxxxxxxxxxx -> sk-****xxxx

        Args:
            token: The token to mask

        Returns:
            Masked token string
        """
        if not token:
            return ""
        if len(token) <= 8:
            return "****"
        return token[:4] + "****" + token[-4:]

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            Base64-encoded key string
        """
        return Fernet.generate_key().decode("utf-8")


# Global crypto service instance
_crypto_service: CryptoService | None = None


def get_crypto_service() -> CryptoService:
    """Get or create the global crypto service instance."""
    global _crypto_service
    if _crypto_service is None:
        from config import get_settings

        settings = get_settings()
        key = settings.encryption_key

        if not key:
            # Auto-generate key if not set (development mode)
            key = CryptoService.generate_key()
            logger.warning(
                "ENCRYPTION_KEY not set. Generated temporary key. "
                "Set ENCRYPTION_KEY in environment for production."
            )

        _crypto_service = CryptoService(key)

    return _crypto_service


def encrypt_value(plaintext: str) -> str:
    """Convenience function to encrypt a value."""
    return get_crypto_service().encrypt(plaintext)


def decrypt_value(ciphertext: str) -> str:
    """Convenience function to decrypt a value."""
    return get_crypto_service().decrypt(ciphertext)


def mask_token(token: str) -> str:
    """Convenience function to mask a token."""
    return CryptoService.mask_token(token)
