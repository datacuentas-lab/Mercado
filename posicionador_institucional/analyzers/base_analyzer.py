"""
Clase base abstracta para todos los analizadores
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """
    Clase base para todos los analizadores de opciones
    Define la interfaz que deben cumplir todos los analizadores
    """
    
    def __init__(self, data_manager=None):
        """
        Inicializar analizador base
        
        Args:
            data_manager: Instancia de DataManager (opcional)
        """
        self.data_manager = data_manager
    
    @abstractmethod
    def analyze(self, options_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Realizar análisis de opciones
        
        Args:
            options_data: DataFrame con datos de opciones
            
        Returns:
            Diccionario con resultados del análisis
        """
        pass
    
    @abstractmethod
    def get_alerts(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generar alertas basadas en resultados de análisis
        
        Args:
            analysis_results: Resultados del análisis
            
        Returns:
            Lista de alertas generadas
        """
        pass
    
    def _validar_datos(self, df: pd.DataFrame, requerido: bool = True) -> bool:
        """
        Validar que el DataFrame contiene datos válidos
        
        Args:
            df: DataFrame a validar
            requerido: Si los datos son requeridos
            
        Returns:
            True si los datos son válidos
        """
        if df is None or df.empty:
            return not requerido
        return True
    
    def _obtener_sector(self, symbol: str) -> str:
        """
        Obtener sector de un símbolo
        
        Args:
            symbol: Símbolo a buscar
            
        Returns:
            Nombre del sector o 'Unknown'
        """
        from ..config import Config
        return Config.get_símbolo_sector(symbol)
