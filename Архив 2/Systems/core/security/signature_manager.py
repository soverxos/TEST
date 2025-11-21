# core/security/signature_manager.py
"""
Система цифровых подписей модулей
Обеспечивает проверку целостности и подлинности модулей с использованием настоящей криптографии
"""

import os
import json
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from loguru import logger

from .crypto_manager import CryptoManager, DigitalSignature

@dataclass
class SignatureVerificationResult:
    """Результат проверки подписи"""
    is_valid: bool
    is_trusted: bool
    error_message: Optional[str] = None
    signer_reputation: Optional[str] = None
    key_id: Optional[str] = None

class ModuleSignatureManager:
    """Менеджер цифровых подписей модулей с настоящей криптографией"""
    
    def __init__(self, config):
        self.config = config
        self.signatures_dir = config.core.project_data_path / "Security" / "signatures"
        self.trusted_keys_dir = config.core.project_data_path / "Security" / "trusted_keys"
        self.signatures_dir.mkdir(parents=True, exist_ok=True)
        self.trusted_keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Инициализируем менеджер криптографии
        self.crypto_manager = CryptoManager(config)
        
        # Список доверенных подписантов
        self.trusted_signers = self._load_trusted_signers()
        
        logger.info(f"[Security] ModuleSignatureManager инициализирован с криптографией. Доверенных подписантов: {len(self.trusted_signers)}")
    
    def _load_trusted_signers(self) -> Dict[str, Dict]:
        """Загружает список доверенных подписантов"""
        trusted_file = self.trusted_keys_dir / "trusted_signers.json"
        
        if trusted_file.exists():
            try:
                with open(trusted_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[Security] Ошибка загрузки доверенных подписантов: {e}")
        
        # Создаем базовый список доверенных подписантов
        default_trusted = {
            "sdb_core_team": {
                "name": "SDB Core Team",
                "email": "core@sdb.dev",
                "key_id": "SDB-CORE-2024",
                "reputation": "trusted",
                "description": "Официальная команда разработки SDB"
            }
        }
        
        self._save_trusted_signers(default_trusted)
        return default_trusted
    
    def _save_trusted_signers(self, signers: Dict[str, Dict]):
        """Сохраняет список доверенных подписантов"""
        trusted_file = self.trusted_keys_dir / "trusted_signers.json"
        
        try:
            with open(trusted_file, 'w', encoding='utf-8') as f:
                json.dump(signers, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[Security] Ошибка сохранения доверенных подписантов: {e}")
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Вычисляет хэш файла"""
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                return hashlib.sha256(file_content).hexdigest()
        except Exception as e:
            logger.error(f"[Security] Ошибка вычисления хэша файла {file_path}: {e}")
            return ""
    
    def sign_module(self, module_path: Path, key_id: str) -> bool:
        """Подписывает модуль с использованием настоящей криптографии"""
        try:
            if not module_path.exists():
                logger.error(f"[Security] Файл модуля не найден: {module_path}")
                return False
            
            # Подписываем модуль
            digital_signature = self.crypto_manager.sign_module(module_path, key_id)
            
            # Сохраняем подпись
            signature_file = self.signatures_dir / f"{module_path.stem}.sig"
            signature_data = {
                "module_name": digital_signature.module_name,
                "version": digital_signature.version,
                "file_hash": digital_signature.file_hash,
                "signature": digital_signature.signature.hex(),  # Конвертируем в hex для JSON
                "signer_key_id": digital_signature.signer_key_id,
                "timestamp": digital_signature.timestamp,
                "algorithm": digital_signature.algorithm
            }
            
            with open(signature_file, 'w', encoding='utf-8') as f:
                json.dump(signature_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[Security] Модуль {module_path.stem} успешно подписан ключом {key_id}")
            return True
            
        except Exception as e:
            logger.error(f"[Security] Ошибка подписания модуля {module_path}: {e}")
            return False
    
    def _generate_signature(self, data: Dict, private_key_path: Optional[Path] = None) -> str:
        """Генерирует цифровую подпись (упрощенная версия)"""
        # В реальной реализации здесь будет GPG подпись
        # Пока используем хэш от данных
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def verify_signature(self, module_path: Path) -> SignatureVerificationResult:
        """Проверяет подпись модуля с использованием настоящей криптографии"""
        try:
            signature_file = self.signatures_dir / f"{module_path.stem}.sig"
            
            if not signature_file.exists():
                return SignatureVerificationResult(
                    is_valid=False,
                    is_trusted=False,
                    error_message="Подпись модуля не найдена"
                )
            
            # Загружаем подпись
            with open(signature_file, 'r', encoding='utf-8') as f:
                signature_data = json.load(f)
            
            # Создаем объект цифровой подписи
            digital_signature = DigitalSignature(
                module_name=signature_data["module_name"],
                version=signature_data["version"],
                file_hash=signature_data["file_hash"],
                signature=bytes.fromhex(signature_data["signature"]),  # Конвертируем из hex
                signer_key_id=signature_data["signer_key_id"],
                timestamp=signature_data["timestamp"],
                algorithm=signature_data["algorithm"]
            )
            
            # Проверяем подпись с использованием криптографии
            is_valid = self.crypto_manager.verify_module_signature(module_path, digital_signature)
            
            if not is_valid:
                return SignatureVerificationResult(
                    is_valid=False,
                    is_trusted=False,
                    error_message="Подпись модуля недействительна",
                    key_id=digital_signature.signer_key_id
                )
            
            # Проверяем, является ли подписант доверенным
            key_id = digital_signature.signer_key_id
            is_trusted = key_id in self.trusted_signers
            
            return SignatureVerificationResult(
                is_valid=True,
                is_trusted=is_trusted,
                signer_reputation=self.trusted_signers.get(key_id, {}).get("reputation") if is_trusted else None,
                key_id=key_id
            )
            
        except Exception as e:
            logger.error(f"[Security] Ошибка проверки подписи модуля {module_path}: {e}")
            return SignatureVerificationResult(
                is_valid=False,
                is_trusted=False,
                error_message=f"Ошибка проверки подписи: {e}"
            )
    
    def add_trusted_signer(self, signer_id: str, signer_info: Dict) -> bool:
        """Добавляет доверенного подписанта"""
        try:
            self.trusted_signers[signer_id] = signer_info
            self._save_trusted_signers(self.trusted_signers)
            logger.info(f"[Security] Добавлен доверенный подписант: {signer_id}")
            return True
        except Exception as e:
            logger.error(f"[Security] Ошибка добавления доверенного подписанта {signer_id}: {e}")
            return False
    
    def remove_trusted_signer(self, signer_id: str) -> bool:
        """Удаляет доверенного подписанта"""
        try:
            if signer_id in self.trusted_signers:
                del self.trusted_signers[signer_id]
                self._save_trusted_signers(self.trusted_signers)
                logger.info(f"[Security] Удален доверенный подписант: {signer_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"[Security] Ошибка удаления доверенного подписанта {signer_id}: {e}")
            return False
    
    def list_trusted_signers(self) -> Dict[str, Dict]:
        """Возвращает список доверенных подписантов"""
        return self.trusted_signers.copy()
    
    def get_module_signature_info(self, module_name: str) -> Optional[Dict]:
        """Возвращает информацию о подписи модуля"""
        signature_file = self.signatures_dir / f"{module_name}.sig"
        
        if not signature_file.exists():
            return None
        
        try:
            with open(signature_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[Security] Ошибка загрузки информации о подписи модуля {module_name}: {e}")
            return None
    
    def generate_signing_key(self, key_id: str, key_size: int = 2048) -> bool:
        """Генерирует новую пару ключей для подписания"""
        try:
            self.crypto_manager.generate_key_pair(key_id, key_size)
            logger.info(f"[Security] Сгенерирована новая пара ключей для подписания: {key_id}")
            return True
        except Exception as e:
            logger.error(f"[Security] Ошибка генерации ключей {key_id}: {e}")
            return False
    
    def export_public_key(self, key_id: str) -> Optional[bytes]:
        """Экспортирует публичный ключ для распространения"""
        try:
            return self.crypto_manager.export_public_key(key_id)
        except Exception as e:
            logger.error(f"[Security] Ошибка экспорта публичного ключа {key_id}: {e}")
            return None
    
    def import_trusted_public_key(self, key_id: str, public_key_pem: bytes) -> bool:
        """Импортирует доверенный публичный ключ"""
        try:
            # Сохраняем публичный ключ
            public_key_file = self.trusted_keys_dir / f"{key_id}.public"
            with open(public_key_file, 'wb') as f:
                f.write(public_key_pem)
            os.chmod(public_key_file, 0o644)
            
            # Добавляем в список доверенных
            self.trusted_signers[key_id] = {
                "name": f"Imported Key {key_id}",
                "email": "unknown@example.com",
                "key_id": key_id,
                "reputation": "trusted",
                "description": "Импортированный доверенный ключ",
                "imported_at": time.time()
            }
            
            self._save_trusted_signers(self.trusted_signers)
            
            logger.info(f"[Security] Импортирован доверенный публичный ключ: {key_id}")
            return True
            
        except Exception as e:
            logger.error(f"[Security] Ошибка импорта доверенного ключа {key_id}: {e}")
            return False
    
    def list_available_keys(self) -> List[str]:
        """Возвращает список доступных ключей"""
        return self.crypto_manager.list_available_keys()
