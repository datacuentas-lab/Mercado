"""
Análisis de eventos próximos y patrones pre-evento
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import pandas as pd

from .base_analyzer import BaseAnalyzer
from ..config import Config

logger = logging.getLogger(__name__)


class EventsAnalyzer(BaseAnalyzer):
    """Analizador de eventos próximos en la agenda económica"""
    
    def __init__(self, data_manager=None):
        """
        Inicializa el analizador de eventos
        
        Args:
            data_manager: Instancia de DataManager para obtener datos
        """
        super().__init__(data_manager)
        self.config = Config()
    
    def detectar_eventos_próximos(
        self,
        símbolo: str,
        días_adelante: int = 90
    ) -> List[Dict]:
        """
        Detecta eventos próximos relevantes para un símbolo
        
        Args:
            símbolo: Símbolo a analizar
            días_adelante: Días hacia el futuro a buscar
            
        Returns:
            Lista de eventos próximos
        """
        fecha_actual = datetime.now()
        fecha_límite = fecha_actual + timedelta(days=días_adelante)
        
        eventos = []
        
        for tipo_evento, fechas in self.config.EVENTOS_CALENDARIO.items():
            for fecha in fechas:
                if fecha_actual <= fecha <= fecha_límite:
                    días_restantes = (fecha - fecha_actual).days
                    evento = {
                        'símbolo': símbolo,
                        'tipo': tipo_evento,
                        'fecha': fecha,
                        'días_restantes': días_restantes,
                        'sector': self._obtener_sector(símbolo),
                    }
                    eventos.append(evento)
        
        return eventos
    
    def analizar_volumen_pre_evento(
        self,
        opciones_data: pd.DataFrame,
        evento: Dict
    ) -> Dict:
        """
        Analiza patrones de volumen antes del evento
        
        Args:
            opciones_data: DataFrame con datos de opciones
            evento: Información del evento
            
        Returns:
            Métricas de volumen pre-evento
        """
        if opciones_data.empty:
            return {}
        
        # Calcular Put/Call ratio
        total_calls = opciones_data[opciones_data['tipo'] == 'CALL']['volume'].sum()
        total_puts = opciones_data[opciones_data['tipo'] == 'PUT']['volume'].sum()
        
        pcr_ratio = total_puts / total_calls if total_calls > 0 else 0
        
        # Distribución ITM/OTM
        itm_calls = opciones_data[
            (opciones_data['tipo'] == 'CALL') & 
            (opciones_data['moneyness'] > 1)
        ]['volume'].sum()
        
        otm_calls = opciones_data[
            (opciones_data['tipo'] == 'CALL') & 
            (opciones_data['moneyness'] <= 1)
        ]['volume'].sum()
        
        itm_puts = opciones_data[
            (opciones_data['tipo'] == 'PUT') & 
            (opciones_data['moneyness'] < 1)
        ]['volume'].sum()
        
        otm_puts = opciones_data[
            (opciones_data['tipo'] == 'PUT') & 
            (opciones_data['moneyness'] >= 1)
        ]['volume'].sum()
        
        return {
            'pcr_ratio': pcr_ratio,
            'itm_calls': itm_calls,
            'otm_calls': otm_calls,
            'itm_puts': itm_puts,
            'otm_puts': otm_puts,
            'total_volumen': opciones_data['volume'].sum(),
        }
    
    def analyze(self, símbolo: str, opciones_data: pd.DataFrame = None, **kwargs) -> Dict:
        """
        Analiza eventos próximos para un símbolo
        
        Args:
            símbolo: Símbolo a analizar
            opciones_data: DataFrame con datos de opciones (opcional)
            **kwargs: Argumentos adicionales
            
        Returns:
            Diccionario con resultados del análisis
        """
        if not self._validar_datos(opciones_data, requerido=False):
            # Intentar obtener datos si no se proporcionan
            if self.data_manager:
                try:
                    opciones_data = self.data_manager.obtener_datos_opciones(
                        símbolo,
                        vencimientos=['15-Nov-24', '20-Dec-24']
                    )
                except Exception as e:
                    logger.warning(f"No se pudieron obtener datos para {símbolo}: {e}")
                    opciones_data = pd.DataFrame()
        
        # Detectar eventos próximos
        eventos_próximos = self.detectar_eventos_próximos(símbolo)
        
        # Analizar volumen pre-evento
        métricas_pre_evento = {}
        for evento in eventos_próximos:
            métricas = self.analizar_volumen_pre_evento(opciones_data, evento)
            evento['volumen_análisis'] = métricas
            métricas_pre_evento[evento['tipo']] = métricas
        
        # Análisis de concentración de vencimientos
        concentración_vencimientos = {}
        if not opciones_data.empty and 'vencimiento' in opciones_data.columns:
            concentración_vencimientos = opciones_data['vencimiento'].value_counts().to_dict()
        
        return {
            'eventos': eventos_próximos,
            'métricas_pre_evento': métricas_pre_evento,
            'concentración_vencimientos': concentración_vencimientos,
            'cantidad_eventos': len(eventos_próximos),
        }
    
    def get_alerts(self, símbolo: str, análisis_resultado: Dict = None) -> List[Dict]:
        """
        Genera alertas basadas en eventos próximos
        
        Args:
            símbolo: Símbolo analizado
            análisis_resultado: Resultado del análisis
            
        Returns:
            Lista de alertas generadas
        """
        alertas = []
        
        if not análisis_resultado:
            return alertas
        
        eventos = análisis_resultado.get('eventos', [])
        
        # Alerta 1: Eventos muy próximos (< 7 días)
        eventos_inminentes = [e for e in eventos if e.get('días_restantes', 999) < 7]
        if eventos_inminentes:
            descripción = f"Evento inminente en {len(eventos_inminentes)} día(s): " + \
                         ", ".join([e['tipo'] for e in eventos_inminentes])
            alertas.append({
                'tipo': 'EVENTO_INMINENTE',
                'prioridad': 'ALTA',
                'descripción': descripción,
                'valor': len(eventos_inminentes),
            })
        
        # Alerta 2: Volumen de opciones anómalo en período pre-evento
        if eventos and 'métricas_pre_evento' in análisis_resultado:
            for tipo_evento, métricas in análisis_resultado['métricas_pre_evento'].items():
                pcr = métricas.get('pcr_ratio', 0)
                
                # Si PCR > 1.5 antes de evento, puede indicar posicionamiento defensivo
                if pcr > 1.5:
                    alertas.append({
                        'tipo': 'VOLUMEN_DEFENSIVO_PRE_EVENTO',
                        'prioridad': 'MEDIA',
                        'descripción': f"Put/Call ratio elevado ({pcr:.2f}) antes de {tipo_evento}",
                        'valor': pcr,
                        'umbral': 1.5,
                    })
                
                # Si PCR < 0.7, posicionamiento ofensivo
                elif pcr > 0 and pcr < 0.7:
                    alertas.append({
                        'tipo': 'VOLUMEN_OFENSIVO_PRE_EVENTO',
                        'prioridad': 'MEDIA',
                        'descripción': f"Put/Call ratio bajo ({pcr:.2f}) antes de {tipo_evento}",
                        'valor': pcr,
                        'umbral': 0.7,
                    })
        
        # Alerta 3: Múltiples eventos en corto plazo
        if len(eventos) > 3:
            alertas.append({
                'tipo': 'MÚLTIPLES_EVENTOS',
                'prioridad': 'MEDIA',
                'descripción': f"Múltiples eventos próximos: {len(eventos)} eventos en próximos 90 días",
                'valor': len(eventos),
            })
        
        return alertas
