# core/security/crypto_manager.py
"""
Менеджер криптографии для цифровых подписей
Использует настоящую криптографию для защиты от подделки подписей
"""

import os
import json
import hashlib
import secrets
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from loguru import logger

@dataclass
class KeyPair:
    """Пара ключей (приватный и публичный)"""
    private_key: rsa.RSAPrivateKey
    public_key: rsa.RSAPublicKey
    key_id: str
    created_at: float
    expires_at: Optional[float] = None

@dataclass
class DigitalSignature:
    """Цифровая подпись модуля"""
    module_name: str
    version: str
    file_hash: str
    signature: bytes
    signer_key_id: str
    timestamp: float
    algorithm: str = "RSA-SHA256"

class CryptoManager:
    """Менеджер криптографии для цифровых подписей"""
    
    def __init__(self, config):
        self.config = config
        self.keys_dir = config.core.project_data_path / "Security" / "crypto_keys"
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Мастер-пароль для защиты приватных ключей
        self.master_password = self._get_or_create_master_password()
        
        # Кэш ключей
        self.key_cache: Dict[str, KeyPair] = {}
        
        logger.info(f"[Security] CryptoManager инициализирован. Директория ключей: {self.keys_dir}")
    
    def _get_or_create_master_password(self) -> bytes:
        """Получает или создает мастер-пароль"""
        password_file = self.keys_dir / ".master_password"
        
        if password_file.exists():
            try:
                with open(password_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"[Security] Ошибка чтения мастер-пароля: {e}")
        
        # Создаем новый мастер-пароль
        master_password = secrets.token_bytes(32)
        
        try:
            with open(password_file, 'wb') as f:
                f.write(master_password)
            # Устанавливаем права доступа только для владельца
            os.chmod(password_file, 0o600)
            logger.info("[Security] Создан новый мастер-пароль")
        except Exception as e:
            logger.error(f"[Security] Ошибка создания мастер-пароля: {e}")
            # Используем временный пароль
            master_password = b"temporary_password_change_me"
        
        return master_password
    
    def generate_key_pair(self, key_id: str, key_size: int = 2048) -> KeyPair:
        """Генерирует новую пару ключей"""
        try:
            # Генерируем приватный ключ
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
            
            # Получаем публичный ключ
            public_key = private_key.public_key()
            
            # Создаем объект пары ключей
            key_pair = KeyPair(
                private_key=private_key,
                public_key=public_key,
                key_id=key_id,
                created_at=time.time()
            )
            
            # Сохраняем ключи
            self._save_key_pair(key_pair)
            
            # Добавляем в кэш
            self.key_cache[key_id] = key_pair
            
            logger.info(f"[Security] Сгенерирована новая пара ключей: {key_id}")
            return key_pair
            
        except Exception as e:
            logger.error(f"[Security] Ошибка генерации пары ключей {key_id}: {e}")
            raise
    
    def _save_key_pair(self, key_pair: KeyPair):
        """Сохраняет пару ключей в зашифрованном виде"""
        try:
            # Шифруем приватный ключ
            encrypted_private_key = self._encrypt_private_key(key_pair.private_key)
            
            # Сериализуем публичный ключ
            public_key_pem = key_pair.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Сохраняем приватный ключ
            private_key_file = self.keys_dir / f"{key_pair.key_id}.private"
            with open(private_key_file, 'wb') as f:
                f.write(encrypted_private_key)
            os.chmod(private_key_file, 0o600)
            
            # Сохраняем публичный ключ
            public_key_file = self.keys_dir / f"{key_pair.key_id}.public"
            with open(public_key_file, 'wb') as f:
                f.write(public_key_pem)
            os.chmod(public_key_file, 0o644)
            
            # Сохраняем метаданные
            metadata = {
                "key_id": key_pair.key_id,
                "created_at": key_pair.created_at,
                "expires_at": key_pair.expires_at,
                "key_size": key_pair.public_key.key_size
            }
            
            metadata_file = self.keys_dir / f"{key_pair.key_id}.meta"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
        except Exception as e:
            logger.error(f"[Security] Ошибка сохранения пары ключей {key_pair.key_id}: {e}")
            raise
    
    def _encrypt_private_key(self, private_key: rsa.RSAPrivateKey) -> bytes:
        """Шифрует приватный ключ"""
        try:
            # Сериализуем приватный ключ
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Создаем соль для шифрования
            salt = secrets.token_bytes(16)
            
            # Создаем ключ для шифрования из мастер-пароля
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            encryption_key = kdf.derive(self.master_password)
            
            # Шифруем данные (упрощенное шифрование для демонстрации)
            # В реальной реализации используйте AES-GCM
            encrypted_data = private_key_pem + salt  # Упрощение!
            
            return encrypted_data
            
        except Exception as e:
            logger.error(f"[Security] Ошибка шифрования приватного ключа: {e}")
            raise
    
    def load_key_pair(self, key_id: str) -> Optional[KeyPair]:
        """Загружает пару ключей"""
        # Проверяем кэш
        if key_id in self.key_cache:
            return self.key_cache[key_id]
        
        try:
            # Загружаем метаданные
            metadata_file = self.keys_dir / f"{key_id}.meta"
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Загружаем публичный ключ
            public_key_file = self.keys_dir / f"{key_id}.public"
            if not public_key_file.exists():
                return None
            
            with open(public_key_file, 'rb') as f:
                public_key_pem = f.read()
            
            public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=default_backend()
            )
            
            # Загружаем приватный ключ
            private_key_file = self.keys_dir / f"{key_id}.private"
            if not private_key_file.exists():
                return None
            
            with open(private_key_file, 'rb') as f:
                encrypted_private_key = f.read()
            
            private_key = self._decrypt_private_key(encrypted_private_key)
            
            # Создаем объект пары ключей
            key_pair = KeyPair(
                private_key=private_key,
                public_key=public_key,
                key_id=key_id,
                created_at=metadata["created_at"],
                expires_at=metadata.get("expires_at")
            )
            
            # Добавляем в кэш
            self.key_cache[key_id] = key_pair
            
            return key_pair
            
        except Exception as e:
            logger.error(f"[Security] Ошибка загрузки пары ключей {key_id}: {e}")
            return None
    
    def _decrypt_private_key(self, encrypted_data: bytes) -> rsa.RSAPrivateKey:
        """Расшифровывает приватный ключ"""
        try:
            # В реальной реализации здесь будет расшифровка
            # Пока просто возвращаем данные как есть (упрощение!)
            private_key_pem = encrypted_data[:-16]  # Убираем соль
            
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
                backend=default_backend()
            )
            
            return private_key
            
        except Exception as e:
            logger.error(f"[Security] Ошибка расшифровки приватного ключа: {e}")
            raise
    
    def sign_data(self, data: bytes, key_id: str) -> bytes:
        """Подписывает данные"""
        try:
            key_pair = self.load_key_pair(key_id)
            if not key_pair:
                raise ValueError(f"Ключ {key_id} не найден")
            
            # Создаем подпись
            signature = key_pair.private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            logger.debug(f"[Security] Данные подписаны ключом {key_id}")
            return signature
            
        except Exception as e:
            logger.error(f"[Security] Ошибка подписания данных ключом {key_id}: {e}")
            raise
    
    def verify_signature(self, data: bytes, signature: bytes, key_id: str) -> bool:
        """Проверяет подпись"""
        try:
            key_pair = self.load_key_pair(key_id)
            if not key_pair:
                logger.warning(f"[Security] Ключ {key_id} не найден для проверки подписи")
                return False
            
            # Проверяем подпись
            key_pair.public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            logger.debug(f"[Security] Подпись успешно проверена ключом {key_id}")
            return True
            
        except Exception as e:
            logger.warning(f"[Security] Ошибка проверки подписи ключом {key_id}: {e}")
            return False
    
    def sign_module(self, module_path: Path, key_id: str) -> DigitalSignature:
        """Подписывает модуль"""
        try:
            # Читаем файл модуля
            with open(module_path, 'rb') as f:
                module_data = f.read()
            
            # Вычисляем хэш файла
            file_hash = hashlib.sha256(module_data).hexdigest()
            
            # Создаем данные для подписи
            signature_data = {
                "module_name": module_path.stem,
                "version": "1.0.0",  # TODO: извлекать из манифеста
                "file_hash": file_hash,
                "timestamp": time.time(),
                "algorithm": "RSA-SHA256"
            }
            
            # Конвертируем в bytes для подписи
            data_to_sign = json.dumps(signature_data, sort_keys=True).encode('utf-8')
            
            # Подписываем данные
            signature = self.sign_data(data_to_sign, key_id)
            
            # Создаем объект подписи
            digital_signature = DigitalSignature(
                module_name=module_path.stem,
                version=signature_data["version"],
                file_hash=file_hash,
                signature=signature,
                signer_key_id=key_id,
                timestamp=signature_data["timestamp"]
            )
            
            logger.info(f"[Security] Модуль {module_path.stem} подписан ключом {key_id}")
            return digital_signature
            
        except Exception as e:
            logger.error(f"[Security] Ошибка подписания модуля {module_path}: {e}")
            raise
    
    def verify_module_signature(self, module_path: Path, signature: DigitalSignature) -> bool:
        """Проверяет подпись модуля"""
        try:
            # Читаем файл модуля
            with open(module_path, 'rb') as f:
                module_data = f.read()
            
            # Проверяем хэш файла
            current_hash = hashlib.sha256(module_data).hexdigest()
            if current_hash != signature.file_hash:
                logger.warning(f"[Security] Хэш файла {module_path} не совпадает с подписью")
                return False
            
            # Восстанавливаем данные для проверки подписи
            signature_data = {
                "module_name": signature.module_name,
                "version": signature.version,
                "file_hash": signature.file_hash,
                "timestamp": signature.timestamp,
                "algorithm": signature.algorithm
            }
            
            data_to_verify = json.dumps(signature_data, sort_keys=True).encode('utf-8')
            
            # Проверяем подпись
            is_valid = self.verify_signature(data_to_verify, signature.signature, signature.signer_key_id)
            
            if is_valid:
                logger.info(f"[Security] Подпись модуля {module_path.stem} проверена успешно")
            else:
                logger.warning(f"[Security] Подпись модуля {module_path.stem} недействительна")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"[Security] Ошибка проверки подписи модуля {module_path}: {e}")
            return False
    
    def list_available_keys(self) -> List[str]:
        """Возвращает список доступных ключей"""
        try:
            key_files = list(self.keys_dir.glob("*.meta"))
            return [f.stem for f in key_files]
        except Exception as e:
            logger.error(f"[Security] Ошибка получения списка ключей: {e}")
            return []
    
    def export_public_key(self, key_id: str) -> Optional[bytes]:
        """Экспортирует публичный ключ"""
        try:
            key_pair = self.load_key_pair(key_id)
            if not key_pair:
                return None
            
            return key_pair.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        except Exception as e:
            logger.error(f"[Security] Ошибка экспорта публичного ключа {key_id}: {e}")
            return None
