"""
Utility functions and helpers
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging


def setup_logging(log_level: str = 'INFO') -> logging.Logger:
    """Configure logging for the application"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('institutional_positioner.log')
        ]
    )
    return logging.getLogger(__name__)


def detectar_eventos_proximos(
    eventos_calendario: Dict[str, List[datetime]],
    dias_adelante: int = 90
) -> List[Dict]:
    """Detect important upcoming events"""
    fecha_actual = datetime.now()
    fecha_limite = fecha_actual + timedelta(days=dias_adelante)
    
    eventos_proximos = [
        {
            'tipo': tipo_evento,
            'fecha': fecha,
            'dias_restantes': (fecha - fecha_actual).days,
        }
        for tipo_evento, fechas in eventos_calendario.items()
        for fecha in fechas
        if fecha_actual <= fecha <= fecha_limite
    ]
    
    return eventos_proximos


def ordenar_alertas_por_prioridad(alertas: List[Dict]) -> List[Dict]:
    """Sort alerts by priority"""
    orden_prioridad = {'ALTA': 1, 'MEDIA': 2, 'BAJA': 3}
    return sorted(
        alertas,
        key=lambda x: orden_prioridad.get(x.get('prioridad', 'BAJA'), 999)
    )


def filtrar_simbolos_con_eventos(
    simbolos: List[str],
    eventos_calendario: Dict[str, List[datetime]],
    sectores: Dict[str, List[str]],
    dias_adelante: int = 90
) -> Dict[str, str]:
    """Returns symbols that have upcoming events"""
    eventos_proximos = detectar_eventos_proximos(eventos_calendario, dias_adelante)
    
    simbolos_con_eventos = {}
    for simbolo in simbolos:
        sector = next(
            (s for s, syms in sectores.items() if simbolo in syms),
            None
        )
        if sector and eventos_proximos:
            simbolos_con_eventos[simbolo] = sector
    
    return simbolos_con_eventos
