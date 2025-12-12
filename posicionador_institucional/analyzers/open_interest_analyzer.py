"""
Analizador de Open Interest
Detecta posiciones institucionales acumuladas a través del Open Interest
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging

from .base_analyzer import BaseAnalyzer
from ..config import Config

logger = logging.getLogger(__name__)


class OpenInterestAnalyzer(BaseAnalyzer):
    """Analiza patrones de Open Interest en opciones"""
    
    def __init__(self, data_manager=None):
        super().__init__(data_manager)
        self.config = Config()
    
    def analyze(self, options_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Realiza análisis detallado del Open Interest
        
        Args:
            options_data: DataFrame con datos de opciones
            
        Returns:
            Diccionario con métricas de Open Interest
        """
        if not self._validar_datos(options_data):
            return {}
        
        analysis = {}
        
        # === MÉTRICAS BÁSICAS DE OI ===
        analysis['oi_total'] = options_data['openInterest'].sum()
        analysis['oi_calls'] = options_data[options_data['tipo'] == 'CALL']['openInterest'].sum()
        analysis['oi_puts'] = options_data[options_data['tipo'] == 'PUT']['openInterest'].sum()
        
        # Ratio Put/Call de Open Interest
        analysis['oi_put_call_ratio'] = (
            analysis['oi_puts'] / analysis['oi_calls']
            if analysis['oi_calls'] > 0 else 0
        )
        
        # === ANÁLISIS DE CONCENTRACIÓN DE OI ===
        # Top 5 strikes por OI
        top_5_oi = options_data.nlargest(5, 'openInterest')['openInterest'].sum()
        total_oi = options_data['openInterest'].sum()
        analysis['oi_concentration'] = (top_5_oi / total_oi * 100) if total_oi > 0 else 0
        
        # === ANÁLISIS ITM/OTM ===
        if 'itm_otm' in options_data.columns:
            oi_itm = options_data[options_data['itm_otm'] == 'ITM']['openInterest'].sum()
            oi_otm = options_data[options_data['itm_otm'] == 'OTM']['openInterest'].sum()
            analysis['oi_itm'] = oi_itm
            analysis['oi_otm'] = oi_otm
            analysis['oi_itm_otm_ratio'] = oi_itm / oi_otm if oi_otm > 0 else 0
        
        # === ANÁLISIS POR VENCIMIENTO ===
        if 'expiration' in options_data.columns:
            oi_por_exp = options_data.groupby('expiration')['openInterest'].sum()
            analysis['oi_vencimiento_cercano'] = oi_por_exp.iloc[0] if len(oi_por_exp) > 0 else 0
            analysis['oi_vencimiento_lejano'] = oi_por_exp.iloc[-1] if len(oi_por_exp) > 0 else 0
        
        # === ANÁLISIS DE STRIKES IMPORTANTES ===
        # Identificar strikes con OI significativo
        oi_por_strike = options_data.groupby('strike')['openInterest'].sum().sort_values(ascending=False)
        analysis['top_strike_oi'] = oi_por_strike.index[0] if len(oi_por_strike) > 0 else None
        analysis['top_strike_oi_value'] = oi_por_strike.iloc[0] if len(oi_por_strike) > 0 else 0
        
        return analysis
    
    def get_alerts(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Genera alertas basadas en análisis de Open Interest
        
        Args:
            analysis_results: Resultados del análisis
            
        Returns:
            Lista de alertas
        """
        alerts = []
        
        # ALERTA 1: Ratio Put/Call OI alto
        if analysis_results.get('oi_put_call_ratio', 0) > 1.3:
            alerts.append({
                'tipo': 'OI_PUTS_EXTREMO',
                'prioridad': 'ALTA',
                'valor': analysis_results['oi_put_call_ratio'],
                'mensaje': f"OI PUT/CALL = {analysis_results['oi_put_call_ratio']:.2f} (Posición defensiva acumulada)"
            })
        
        # ALERTA 2: Concentración alta de OI
        if analysis_results.get('oi_concentration', 0) > 40:
            alerts.append({
                'tipo': 'OI_CONCENTRADO',
                'prioridad': 'MEDIA',
                'valor': analysis_results['oi_concentration'],
                'mensaje': f"OI concentrado: {analysis_results['oi_concentration']:.1f}% en top 5 strikes"
            })
        
        # ALERTA 3: Ratio ITM/OTM anómalo
        oi_ratio = analysis_results.get('oi_itm_otm_ratio', 0)
        if oi_ratio > 1.5 or (oi_ratio > 0 and oi_ratio < 0.3):
            alerts.append({
                'tipo': 'OI_ITM_OTM_ANOMALO',
                'prioridad': 'MEDIA',
                'valor': oi_ratio,
                'mensaje': f"OI ITM/OTM anómalo: {oi_ratio:.2f}"
            })
        
        return alerts
