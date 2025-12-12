"""
Institutional Positioner - Framework de análisis de posicionamiento institucional
en opciones durante escenarios de riesgo de corrección
"""

__version__ = "1.0.0"
__author__ = "Análisis Cuantitativo"

# Evitar importaciones circulares
# Importar solo los módulos base
from .config import Config
from .data import DataManager

__all__ = [
    'Config',
    'DataManager',
]
