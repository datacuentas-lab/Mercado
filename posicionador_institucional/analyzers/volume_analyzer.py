"""
Analizador de volumen de opciones
Detecta patrones anómalos en el volumen de trading institucional
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging

from .base_analyzer import BaseAnalyzer
from ..config import Config

logger = logging.getLogger(__name__)


class VolumeAnalyzer(BaseAnalyzer):
    """Analiza patrones de volumen en opciones"""
    
    def __init__(self, data_manager=None):
        super().__init__(data_manager)
        self.config = Config()
    
    def analyze(self, options_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Realiza análisis detallado del volumen
        
        Args:
            options_data: DataFrame con datos de opciones
            
        Returns:
            Diccionario con métricas de volumen
        """
        if not self._validar_datos(options_data):
            return {}
        
        analysis = {}
        
        # === MÉTRICAS BÁSICAS ===
        analysis['vol_total'] = options_data['volume'].sum()
        analysis['vol_calls'] = options_data[options_data['tipo'] == 'CALL']['volume'].sum()
        analysis['vol_puts'] = options_data[options_data['tipo'] == 'PUT']['volume'].sum()
        
        # Ratio Put/Call por volumen
        analysis['vol_put_call_ratio'] = (
            analysis['vol_puts'] / analysis['vol_calls'] 
            if analysis['vol_calls'] > 0 else 0
        )
        
        # === ANÁLISIS DE CONCENTRACIÓN ===
        # Volumen ITM vs OTM
        if 'itm_otm' in options_data.columns:
            vol_itm = options_data[options_data['itm_otm'] == 'ITM']['volume'].sum()
            vol_otm = options_data[options_data['itm_otm'] == 'OTM']['volume'].sum()
            analysis['vol_itm'] = vol_itm
            analysis['vol_otm'] = vol_otm
            analysis['itm_otm_ratio'] = vol_itm / vol_otm if vol_otm > 0 else 0
        
        # === ANÁLISIS DE LIQUIDEZ ===
        # Rotación (Volumen / Open Interest)
        options_data['vol_oi_individual'] = np.where(
            options_data['openInterest'] > 0,
            options_data['volume'] / options_data['openInterest'],
            0
        )
        analysis['rotación_promedio'] = options_data['vol_oi_individual'].mean()
        analysis['alta_rotación_count'] = len(options_data[options_data['vol_oi_individual'] > 1.0])
        
        # === DETECCIÓN DE ACTIVIDAD INUSUAL ===
        q_percentil = options_data['volume'].quantile(self.config.PERCENTIL_VOLUMEN_ALTO / 100)
        contratos_alta = options_data[options_data['volume'] > q_percentil]
        analysis['contratos_alta_actividad'] = len(contratos_alta)
        analysis['vol_alta_actividad'] = contratos_alta['volume'].sum()
        
        # === SENTIMIENTO PONDERADO ===
        if 'moneyness' in options_data.columns:
            options_data['peso_distancia'] = 1 / (abs(options_data['moneyness'] - 1) + 0.01)
            calls_data = options_data[options_data['tipo'] == 'CALL']
            puts_data = options_data[options_data['tipo'] == 'PUT']
            
            vol_calls_pond = (calls_data['volume'] * calls_data['peso_distancia']).sum()
            vol_puts_pond = (puts_data['volume'] * puts_data['peso_distancia']).sum()
            
            analysis['vol_put_call_ponderado'] = (
                vol_puts_pond / vol_calls_pond if vol_calls_pond > 0 else 0
            )
        
        return analysis
    
    def get_alerts(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Genera alertas basadas en análisis de volumen
        
        Args:
            analysis_results: Resultados del análisis
            
        Returns:
            Lista de alertas
        """
        alerts = []
        
        # ALERTA 1: Ratio Put/Call alto = Posición defensiva institucional
        if analysis_results.get('vol_put_call_ratio', 0) > self.config.UMBRAL_PCR_DEFENSIVO:
            alerts.append({
                'tipo': 'VOLUMEN_PUTS_EXTREMO',
                'prioridad': 'ALTA',
                'valor': analysis_results['vol_put_call_ratio'],
                'mensaje': f"Volumen PUT/CALL = {analysis_results['vol_put_call_ratio']:.2f}"
            })
        
        # ALERTA 2: Alta rotación (Vol >> OI)
        if analysis_results.get('rotación_promedio', 0) > self.config.UMBRAL_ROTACION:
            alerts.append({
                'tipo': 'ALTA_ROTACION',
                'prioridad': 'MEDIA',
                'valor': analysis_results['rotación_promedio'],
                'mensaje': f"Rotación Alta: {analysis_results['rotación_promedio']:.1%}"
            })
        
        # ALERTA 3: Volumen concentrado
        if analysis_results.get('contratos_alta_actividad', 0) > 5:
            alerts.append({
                'tipo': 'CONCENTRACION_VOLUMEN',
                'prioridad': 'MEDIA',
                'valor': analysis_results['contratos_alta_actividad'],
                'mensaje': f"Volumen en {analysis_results['contratos_alta_actividad']} contratos"
            })
        
        return alerts
