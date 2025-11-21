# core/security/code_scanner.py
"""
Автоматический сканер подозрительного кода модулей
Анализирует код на предмет потенциальных угроз безопасности
"""

import ast
import re
import json
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from loguru import logger

class ThreatLevel(Enum):
    """Уровни угроз"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatType(Enum):
    """Типы угроз"""
    MALICIOUS_IMPORT = "malicious_import"
    SYSTEM_COMMAND = "system_command"
    FILE_ACCESS = "file_access"
    NETWORK_REQUEST = "network_request"
    CODE_INJECTION = "code_injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    BACKDOOR = "backdoor"
    CRYPTO_MINING = "crypto_mining"

@dataclass
class SecurityThreat:
    """Угроза безопасности"""
    threat_type: ThreatType
    threat_level: ThreatLevel
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    recommendation: str

@dataclass
class ScanResult:
    """Результат сканирования"""
    module_name: str
    scan_timestamp: float
    threats_found: List[SecurityThreat]
    risk_score: float  # 0-100
    is_safe: bool
    suspicious_patterns: List[str]
    code_metrics: Dict[str, any]

class ModuleCodeScanner:
    """Сканер кода модулей"""
    
    def __init__(self, config):
        self.config = config
        
        # Паттерны подозрительного кода
        self.suspicious_patterns = {
            # Системные команды
            ThreatType.SYSTEM_COMMAND: [
                r'os\.system\(',
                r'subprocess\.',
                r'exec\(',
                r'eval\(',
                r'__import__\(',
                r'compile\(',
                r'execfile\(',
            ],
            
            # Доступ к файлам
            ThreatType.FILE_ACCESS: [
                r'open\(',
                r'file\(',
                r'os\.remove\(',
                r'os\.unlink\(',
                r'shutil\.',
                r'os\.path\.',
            ],
            
            # Сетевые запросы
            ThreatType.NETWORK_REQUEST: [
                r'requests\.',
                r'urllib\.',
                r'socket\.',
                r'http\.',
                r'ftplib\.',
                r'smtplib\.',
            ],
            
            # Инъекция кода
            ThreatType.CODE_INJECTION: [
                r'eval\(',
                r'exec\(',
                r'__import__\(',
                r'getattr\(',
                r'setattr\(',
                r'globals\(',
                r'locals\(',
            ],
            
            # Подозрительные импорты
            ThreatType.MALICIOUS_IMPORT: [
                r'import\s+os',
                r'import\s+subprocess',
                r'import\s+socket',
                r'import\s+urllib',
                r'import\s+requests',
                r'from\s+os\s+import',
                r'from\s+subprocess\s+import',
            ],
            
            # Backdoor паттерны
            ThreatType.BACKDOOR: [
                r'backdoor',
                r'hidden',
                r'secret',
                r'admin',
                r'root',
                r'password',
                r'token',
                r'key',
            ],
            
            # Криптомайнинг
            ThreatType.CRYPTO_MINING: [
                r'mining',
                r'hash',
                r'crypto',
                r'bitcoin',
                r'ethereum',
                r'miner',
            ]
        }
        
        # Веса угроз для расчета общего риска
        self.threat_weights = {
            ThreatLevel.CRITICAL: 1.0,
            ThreatLevel.HIGH: 0.7,
            ThreatLevel.MEDIUM: 0.4,
            ThreatLevel.LOW: 0.1
        }
        
        logger.info(f"[Security] ModuleCodeScanner инициализирован с {len(self.suspicious_patterns)} типами угроз")
    
    def scan_module(self, module_path: Path) -> ScanResult:
        """Сканирует модуль на предмет угроз безопасности"""
        try:
            threats = []
            suspicious_patterns = []
            code_metrics = {}
            
            # Читаем файлы модуля
            python_files = list(module_path.rglob("*.py"))
            
            for file_path in python_files:
                file_threats, file_patterns, file_metrics = self._scan_file(file_path)
                threats.extend(file_threats)
                suspicious_patterns.extend(file_patterns)
                
                # Обновляем метрики
                for key, value in file_metrics.items():
                    code_metrics[key] = code_metrics.get(key, 0) + value
            
            # Вычисляем общий риск
            risk_score = self._calculate_risk_score(threats)
            is_safe = risk_score < 30.0  # Порог безопасности
            
            result = ScanResult(
                module_name=module_path.name,
                scan_timestamp=Path(module_path).stat().st_mtime,
                threats_found=threats,
                risk_score=risk_score,
                is_safe=is_safe,
                suspicious_patterns=list(set(suspicious_patterns)),
                code_metrics=code_metrics
            )
            
            logger.info(f"[Security] Сканирование модуля {module_path.name}: найдено {len(threats)} угроз, риск {risk_score:.1f}")
            return result
            
        except Exception as e:
            logger.error(f"[Security] Ошибка сканирования модуля {module_path}: {e}")
            return ScanResult(
                module_name=module_path.name,
                scan_timestamp=0,
                threats_found=[],
                risk_score=100.0,  # Максимальный риск при ошибке
                is_safe=False,
                suspicious_patterns=[],
                code_metrics={}
            )
    
    def _scan_file(self, file_path: Path) -> Tuple[List[SecurityThreat], List[str], Dict[str, any]]:
        """Сканирует отдельный файл"""
        threats = []
        suspicious_patterns = []
        metrics = {
            "lines_of_code": 0,
            "functions_count": 0,
            "classes_count": 0,
            "imports_count": 0
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                metrics["lines_of_code"] = len(lines)
            
            # Анализ AST
            try:
                tree = ast.parse(content)
                metrics.update(self._analyze_ast(tree))
            except SyntaxError:
                logger.warning(f"[Security] Синтаксическая ошибка в файле {file_path}")
            
            # Поиск подозрительных паттернов
            for line_num, line in enumerate(lines, 1):
                line_threats, line_patterns = self._analyze_line(line, line_num, file_path)
                threats.extend(line_threats)
                suspicious_patterns.extend(line_patterns)
            
        except Exception as e:
            logger.error(f"[Security] Ошибка чтения файла {file_path}: {e}")
        
        return threats, suspicious_patterns, metrics
    
    def _analyze_ast(self, tree: ast.AST) -> Dict[str, int]:
        """Анализирует AST дерево"""
        metrics = {
            "functions_count": 0,
            "classes_count": 0,
            "imports_count": 0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                metrics["functions_count"] += 1
            elif isinstance(node, ast.ClassDef):
                metrics["classes_count"] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                metrics["imports_count"] += 1
        
        return metrics
    
    def _analyze_line(self, line: str, line_num: int, file_path: Path) -> Tuple[List[SecurityThreat], List[str]]:
        """Анализирует отдельную строку кода"""
        threats = []
        patterns = []
        
        # Проверяем каждый тип угроз
        for threat_type, pattern_list in self.suspicious_patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, line, re.IGNORECASE):
                    threat_level = self._determine_threat_level(threat_type, pattern, line)
                    
                    threat = SecurityThreat(
                        threat_type=threat_type,
                        threat_level=threat_level,
                        file_path=str(file_path),
                        line_number=line_num,
                        code_snippet=line.strip(),
                        description=self._get_threat_description(threat_type),
                        recommendation=self._get_threat_recommendation(threat_type)
                    )
                    
                    threats.append(threat)
                    patterns.append(f"{threat_type.value}: {pattern}")
        
        return threats, patterns
    
    def _determine_threat_level(self, threat_type: ThreatType, pattern: str, line: str) -> ThreatLevel:
        """Определяет уровень угрозы"""
        # Критические угрозы
        if threat_type in [ThreatType.CODE_INJECTION, ThreatType.PRIVILEGE_ESCALATION]:
            return ThreatLevel.CRITICAL
        
        # Высокие угрозы
        if threat_type in [ThreatType.SYSTEM_COMMAND, ThreatType.BACKDOOR]:
            return ThreatLevel.HIGH
        
        # Средние угрозы
        if threat_type in [ThreatType.FILE_ACCESS, ThreatType.NETWORK_REQUEST]:
            return ThreatLevel.MEDIUM
        
        # Низкие угрозы
        return ThreatLevel.LOW
    
    def _get_threat_description(self, threat_type: ThreatType) -> str:
        """Возвращает описание угрозы"""
        descriptions = {
            ThreatType.MALICIOUS_IMPORT: "Подозрительный импорт системных модулей",
            ThreatType.SYSTEM_COMMAND: "Выполнение системных команд",
            ThreatType.FILE_ACCESS: "Доступ к файловой системе",
            ThreatType.NETWORK_REQUEST: "Сетевые запросы",
            ThreatType.CODE_INJECTION: "Инъекция кода",
            ThreatType.PRIVILEGE_ESCALATION: "Попытка повышения привилегий",
            ThreatType.DATA_EXFILTRATION: "Возможная утечка данных",
            ThreatType.BACKDOOR: "Подозрение на backdoor",
            ThreatType.CRYPTO_MINING: "Подозрение на криптомайнинг"
        }
        return descriptions.get(threat_type, "Неизвестная угроза")
    
    def _get_threat_recommendation(self, threat_type: ThreatType) -> str:
        """Возвращает рекомендацию по устранению угрозы"""
        recommendations = {
            ThreatType.MALICIOUS_IMPORT: "Проверьте необходимость импорта системных модулей",
            ThreatType.SYSTEM_COMMAND: "Избегайте выполнения системных команд",
            ThreatType.FILE_ACCESS: "Ограничьте доступ к файловой системе",
            ThreatType.NETWORK_REQUEST: "Проверьте необходимость сетевых запросов",
            ThreatType.CODE_INJECTION: "Никогда не используйте eval() или exec()",
            ThreatType.PRIVILEGE_ESCALATION: "Не пытайтесь повышать привилегии",
            ThreatType.DATA_EXFILTRATION: "Проверьте обработку пользовательских данных",
            ThreatType.BACKDOOR: "Удалите подозрительный код",
            ThreatType.CRYPTO_MINING: "Удалите код, связанный с майнингом"
        }
        return recommendations.get(threat_type, "Обратитесь к документации по безопасности")
    
    def _calculate_risk_score(self, threats: List[SecurityThreat]) -> float:
        """Вычисляет общий риск модуля"""
        if not threats:
            return 0.0
        
        total_score = 0.0
        total_weight = 0.0
        
        for threat in threats:
            weight = self.threat_weights.get(threat.threat_level, 0.1)
            total_score += weight * 100  # Максимальный балл за угрозу
            total_weight += weight
        
        if total_weight > 0:
            return min(100.0, total_score / total_weight)
        
        return 0.0
    
    def get_scan_summary(self, scan_result: ScanResult) -> Dict[str, any]:
        """Возвращает краткое резюме сканирования"""
        threat_counts = {}
        for threat in scan_result.threats_found:
            level = threat.threat_level.value
            threat_counts[level] = threat_counts.get(level, 0) + 1
        
        return {
            "module_name": scan_result.module_name,
            "is_safe": scan_result.is_safe,
            "risk_score": scan_result.risk_score,
            "total_threats": len(scan_result.threats_found),
            "threat_counts": threat_counts,
            "suspicious_patterns_count": len(scan_result.suspicious_patterns),
            "code_metrics": scan_result.code_metrics
        }
