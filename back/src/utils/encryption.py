"""
Encryption utilities for secure API key storage using Fernet symmetric encryption
"""

import base64
import os
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..models.security import EncryptionResult


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service
        
        Args:
            encryption_key: Base64 encoded encryption key. If not provided,
                          will use ENCRYPTION_KEY environment variable
        """
        self.encryption_key = encryption_key or os.getenv("ENCRYPTION_KEY")
        if not self.encryption_key:
            raise ValueError("ENCRYPTION_KEY environment variable not set")
        
        # Derive Fernet key from the provided key
        self.fernet = Fernet(self.encryption_key.encode())
    
    def encrypt_data(self, data: str) -> EncryptionResult:
        """
        Encrypt sensitive data
        
        Args:
            data: Plaintext data to encrypt
            
        Returns:
            EncryptionResult containing encrypted data and key identifier
        """
        if not data:
            raise ValueError("Data cannot be empty")
        
        encrypted_data = self.fernet.encrypt(data.encode())
        
        return EncryptionResult(
            encrypted_data=encrypted_data.decode(),
            key_id=self._get_key_id()
        )
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted plaintext data
        """
        if not encrypted_data:
            raise ValueError("Encrypted data cannot be empty")
        
        try:
            decrypted_data = self.fernet.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    def _get_key_id(self) -> str:
        """Generate a key identifier based on the encryption key"""
        # Use first 8 bytes of the key hash as identifier
        key_bytes = self.encryption_key.encode()
        hash_obj = hashes.Hash(hashes.SHA256())
        hash_obj.update(key_bytes)
        key_hash = hash_obj.finalize()
        return base64.urlsafe_b64encode(key_hash[:8]).decode()
    
    def rotate_key(self, new_encryption_key: str, reencrypt_callback: callable) -> bool:
        """
        Rotate encryption key and re-encrypt all data
        
        Args:
            new_encryption_key: New base64 encoded encryption key
            reencrypt_callback: Function that returns all encrypted data to re-encrypt
            
        Returns:
            True if rotation was successful
        """
        try:
            old_fernet = self.fernet
            
            # Create new Fernet instance with new key
            new_fernet = Fernet(new_encryption_key.encode())
            
            # Get all data that needs re-encryption
            data_to_reencrypt = reencrypt_callback()
            
            # Re-encrypt all data
            reencrypted_data = []
            for encrypted_item in data_to_reencrypt:
                try:
                    # Decrypt with old key
                    decrypted = old_fernet.decrypt(encrypted_item.encode())
                    # Encrypt with new key
                    reencrypted = new_fernet.encrypt(decrypted)
                    reencrypted_data.append(reencrypted.decode())
                except Exception as e:
                    # Log error but continue with other items
                    print(f"Failed to re-encrypt item: {e}")
                    continue
            
            # Update service to use new key
            self.encryption_key = new_encryption_key
            self.fernet = new_fernet
            
            return True
            
        except Exception as e:
            print(f"Key rotation failed: {e}")
            return False


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key
    
    Returns:
        Base64 encoded encryption key
    """
    return Fernet.generate_key().decode()


def derive_key_from_password(password: str, salt: bytes) -> str:
    """
    Derive encryption key from password using PBKDF2
    
    Args:
        password: Password to derive key from
        salt: Random salt for key derivation
        
    Returns:
        Base64 encoded derived key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(key).decode()


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get or create global encryption service instance
    
    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_key(api_key: str) -> EncryptionResult:
    """
    Encrypt an API key
    
    Args:
        api_key: Plaintext API key to encrypt
        
    Returns:
        EncryptionResult with encrypted data
    """
    service = get_encryption_service()
    return service.encrypt_data(api_key)


def decrypt_key(encrypted_key: str) -> str:
    """
    Decrypt an encrypted API key
    
    Args:
        encrypted_key: Encrypted API key
        
    Returns:
        Decrypted plaintext API key
    """
    service = get_encryption_service()
    return service.decrypt_data(encrypted_key)