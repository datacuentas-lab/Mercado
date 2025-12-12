"""
Modelos de datos para opciones y análisis
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import pandas as pd


@dataclass
class OptionsChain:
    """Cadena de opciones para un símbolo"""
    symbol: str
    underlying_price: float
    expiration_date: str
    calls: pd.DataFrame
    puts: pd.DataFrame
    
    @property
    def total_volume(self) -> float:
        """Volumen total de calls y puts"""
        return self.calls['volume'].sum() + self.puts['volume'].sum()
    
    @property
    def call_volume(self) -> float:
        return self.calls['volume'].sum()
    
    @property
    def put_volume(self) -> float:
        return self.puts['volume'].sum()


@dataclass
class VolumeAnalysisResult:
    """Resultado del análisis de volumen"""
    symbol: str
    sector: str
    vol_total: float
    vol_calls: float
    vol_puts: float
    vol_put_call_ratio: float
    rotación_promedio: float
    alta_rotación_count: int
    contratos_alta_actividad: int
    vol_alta_actividad: float
    vol_put_call_ponderado: float
    vol_itm: float
    vol_otm: float
    itm_otm_ratio: float


@dataclass
class OpenInterestAnalysisResult:
    """Resultado del análisis de Open Interest"""
    symbol: str
    sector: str
    oi_total: float
    oi_calls: float
    oi_puts: float
    oi_put_call_ratio: float
    oi_concentration: float  # % de OI en top 5 strikes


@dataclass
class EventData:
    """Datos de un evento importante"""
    tipo: str
    fecha: str
    días_restantes: int
    symbol: str


@dataclass
class Alert:
    """Alerta generada por el sistema"""
    tipo: str
    prioridad: str  # ALTA, MEDIA, BAJA
    sector: str
    symbol: str
    valor: float
    mensaje: str
    evento: Optional[Dict[str, Any]] = None
