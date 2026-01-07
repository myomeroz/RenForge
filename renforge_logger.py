"""
RenForge Merkezi Logging Modülü

Tüm uygulama için standart logging yapılandırması sağlar.
Log dosyaları ~/.renforge/logs/ dizininde saklanır.
"""

import logging
import os
from pathlib import Path
from datetime import datetime

# Log dizini
LOG_DIR = Path.home() / ".renforge" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log dosyası adı (tarih ile)
LOG_FILE = LOG_DIR / f"renforge_{datetime.now().strftime('%Y%m%d')}.log"

# Log formatı
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Belirtilen isimle bir logger oluşturur veya mevcut olanı döndürür.
    
    Args:
        name: Logger adı (genellikle modül adı)
        level: Log seviyesi (varsayılan: DEBUG)
    
    Returns:
        Yapılandırılmış Logger nesnesi
    """
    logger = logging.getLogger(name)
    
    # Eğer handler zaten eklenmişse tekrar ekleme
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Konsol handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Konsola sadece INFO ve üstü
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # Dosya handler
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Dosyaya tüm seviyeleri yaz
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# Ana uygulama logger'ı
logger = setup_logger("renforge")


def get_logger(name: str) -> logging.Logger:
    """
    Modül için child logger döndürür.
    
    Args:
        name: Modül adı
    
    Returns:
        renforge.{name} formatında logger
    """
    return setup_logger(f"renforge.{name}")
