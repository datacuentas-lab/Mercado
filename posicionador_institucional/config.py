"""
Configuración centralizada del sistema de análisis de posicionamiento institucional
"""

from datetime import datetime, timedelta


class Config:
    """Clase de configuración centralizada"""
    
    # ============================================================================
    # CONFIGURACIÓN DE SECTORES
    # ============================================================================
    SECTORES = {
        'Indices': ['SPY', 'QQQ', 'IWM', 'DIA'],
        'Tecnologicas': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA'],
        'Energia': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC'],
        'Financieras': ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
        'Salud': ['JNJ', 'PFE', 'UNH', 'MRK', 'ABT']
    }
    
    # ============================================================================
    # CONFIGURACIÓN DE EVENTOS
    # ============================================================================
    EVENTOS_CALENDARIO = {
        'earnings_season': [
            datetime(2025, 1, 15),
            datetime(2025, 4, 15),
            datetime(2025, 7, 15),
            datetime(2025, 10, 15),
            datetime(2026, 1, 20),
            datetime(2026, 4, 15),
        ],
        'fomc_meetings': [
            datetime(2025, 1, 29),
            datetime(2025, 3, 19),
            datetime(2025, 5, 7),
            datetime(2025, 6, 18),
            datetime(2025, 7, 30),
            datetime(2025, 9, 17),
            datetime(2025, 11, 5),
            datetime(2025, 12, 17),
            datetime(2026, 1, 27),
            datetime(2026, 3, 17),
        ],
        'quad_witching': [
            datetime(2025, 3, 21),
            datetime(2025, 6, 20),
            datetime(2025, 9, 19),
            datetime(2025, 12, 19),
            datetime(2026, 3, 20),
        ]
    }
    
    # ============================================================================
    # CONFIGURACIÓN DE DATOS
    # ============================================================================
    # Número de vencimientos a analizar por símbolo
    NUM_VENCIMIENTOS = 3
    
    # Días de vencimiento a buscar
    DIAS_VENCIMIENTO = 30
    
    # Vencimientos por defecto
    VENCIMIENTOS_OPCIONES = ['15-Nov-24', '20-Dec-24', '24-Jan-25']
    
    # ============================================================================
    # CONFIGURACIÓN DE ANÁLISIS DE VOLUMEN
    # ============================================================================
    # Umbral Put/Call Ratio para alerta ALTA
    UMBRAL_PCR_DEFENSIVO = 1.2
    
    # Umbral de rotación (Vol/OI) para alerta
    UMBRAL_ROTACION = 0.8
    
    # Percentil para detectar volumen alto
    PERCENTIL_VOLUMEN_ALTO = 95
    
    # ============================================================================
    # CONFIGURACIÓN DE EVENTOS
    # ============================================================================
    # Días adelante para buscar eventos próximos
    DIAS_ADELANTE_EVENTOS = 90
    
    # ============================================================================
    # CONFIGURACIÓN DE VISUALIZACIÓN
    # ============================================================================
    FIGURA_SIZE = (20, 12)
    DPI_GUARDADO = 100
    ARCHIVO_GRAFICO = 'analisis_volumen_opciones.png'
    
    # ============================================================================
    # CONFIGURACIÓN DE LOGGING
    # ============================================================================
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'institutional_positioner.log'
    
    @classmethod
    def get_todos_símbolos(cls) -> list:
        """Retorna lista de todos los símbolos"""
        símbolos = []
        for sector_symbols in cls.SECTORES.values():
            símbolos.extend(sector_symbols)
        return símbolos
    
    @classmethod
    def get_símbolo_sector(cls, símbolo: str) -> str:
        """Retorna el sector de un símbolo"""
        for sector, símbolos in cls.SECTORES.items():
            if símbolo in símbolos:
                return sector
        return 'Unknown'
