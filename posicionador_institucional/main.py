"""
Archivo principal - Orquestador del análisis de posicionamiento institucional
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from institutional_positioner.config import Config
from institutional_positioner.data import DataManager
from institutional_positioner.analyzers import (
    VolumeAnalyzer,
    OpenInterestAnalyzer,
    EventsAnalyzer,
)
from institutional_positioner.reporting import ReportGenerator
from institutional_positioner.utils import (
    setup_logging,
    detectar_eventos_proximos,
    filtrar_simbolos_con_eventos,
)


logger = logging.getLogger(__name__)


class AnalisisInstPosiciones:
    """Orquestador principal del análisis de posicionamiento institucional"""
    
    def __init__(self, output_dir: str = "reportes"):
        """
        Inicializa el analizador
        
        Args:
            output_dir: Directorio para guardar reportes
        """
        self.config = Config()
        self.data_manager = DataManager()
        
        # Inicializar analizadores
        self.volume_analyzer = VolumeAnalyzer(self.data_manager)
        self.oi_analyzer = OpenInterestAnalyzer(self.data_manager)
        self.events_analyzer = EventsAnalyzer(self.data_manager)
        
        # Inicializar generador de reportes
        self.report_generator = ReportGenerator(output_dir)
        
        logger.info("Analizador de posicionamiento institucional inicializado")
    
    def obtener_simbolos_con_eventos(self) -> Dict[str, str]:
        """
        Obtiene símbolos que tienen eventos próximos
        
        Returns:
            Diccionario {símbolo: sector}
        """
        return filtrar_simbolos_con_eventos(
            self.config.get_todos_simbolos(),
            self.config.EVENTOS_CALENDARIO,
            self.config.SECTORES,
            dias_adelante=90
        )
    
    def ejecutar_análisis_símbolo(
        self,
        símbolo: str,
        num_vencimientos: int = 3
    ) -> Dict:
        """
        Ejecuta todos los análisis para un símbolo
        
        Args:
            símbolo: Símbolo a analizar
            num_vencimientos: Número de vencimientos a obtener
            
        Returns:
            Resultados consolidados de todos los analizadores
        """
        logger.info(f"Analizando {símbolo}...")
        
        resultados = {}
        
        try:
            # Obtener datos
            opciones_data = self.data_manager.obtener_datos_opciones(
                símbolo, 
                num_vencimientos=num_vencimientos
            )
            
            if opciones_data is None or opciones_data.empty:
                logger.warning(f"No hay datos para {símbolo}")
                return resultados
            
            # Análisis de volumen
            vol_result = self.volume_analyzer.analyze(opciones_data)
            vol_alerts = self.volume_analyzer.get_alerts(vol_result)
            resultados['volume_analyzer'] = {
                'metrics': vol_result,
                'alerts': vol_alerts
            }
            
            # Análisis de Open Interest
            oi_result = self.oi_analyzer.analyze(opciones_data)
            oi_alerts = self.oi_analyzer.get_alerts(oi_result)
            resultados['open_interest_analyzer'] = {
                'metrics': oi_result,
                'alerts': oi_alerts
            }
            
            # Análisis de eventos
            events_result = self.events_analyzer.analyze(símbolo, opciones_data)
            events_alerts = self.events_analyzer.get_alerts(símbolo, events_result)
            resultados['events_analyzer'] = {
                'metrics': events_result,
                'alerts': events_alerts,
                'eventos': events_result.get('eventos', [])
            }
            
            logger.info(f"✓ {símbolo}: {len(vol_alerts + oi_alerts + events_alerts)} alertas generadas")
            
        except Exception as e:
            logger.error(f"Error analizando {símbolo}: {e}", exc_info=True)
        
        return resultados
    
    def ejecutar_análisis_completo(
        self,
        símbolos: Optional[List[str]] = None,
        por_sector: bool = False
    ) -> Dict:
        """
        Ejecuta análisis completo para múltiples símbolos
        
        Args:
            símbolos: Lista de símbolos a analizar (None = todos)
            por_sector: Si True, organiza resultados por sector
            
        Returns:
            Diccionario con resultados por símbolo
        """
        inicio = datetime.now()
        logger.info(f"Iniciando análisis completo - {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if símbolos is None:
            símbolos = self.config.get_todos_símbolos()
        
        todos_resultados = {}
        eventos_detectados_global = []
        
        # Ejecutar análisis por símbolo
        for símbolo in símbolos:
            resultado = self.ejecutar_análisis_símbolo(símbolo)
            todos_resultados[símbolo] = resultado
            
            # Acumular eventos detectados
            if 'events_analyzer' in resultado:
                eventos = resultado['events_analyzer'].get('eventos', [])
                eventos_detectados_global.extend(eventos)
        
        # Consolidar alertas
        alertas_consolidadas = self.report_generator.consolidar_alertas(todos_resultados)
        
        # Generar visualizaciones
        archivo_gráfico = self.report_generator.visualizar_análisis_volumen(
            todos_resultados,
            eventos_detectados_global,
            nombre_archivo="análisis_volumen.png"
        )
        
        # Generar reporte de alertas
        reporte_alertas = self.report_generator.generar_alertas_volumen(alertas_consolidadas)
        archivo_reporte = self.report_generator.guardar_reporte_texto(
            reporte_alertas,
            nombre_archivo="alertas.txt"
        )
        
        # Imprimir resumen
        print(reporte_alertas)
        
        tiempo_total = (datetime.now() - inicio).total_seconds()
        
        logger.info(f"\n{'='*80}")
        logger.info(f"ANÁLISIS COMPLETADO")
        logger.info(f"{'='*80}")
        logger.info(f"Símbolos analizados: {len(todos_resultados)}")
        logger.info(f"Total alertas: {len(alertas_consolidadas)}")
        logger.info(f"Eventos detectados: {len(eventos_detectados_global)}")
        logger.info(f"Tiempo de ejecución: {tiempo_total:.2f} segundos")
        logger.info(f"Gráfico guardado: {archivo_gráfico}")
        logger.info(f"Reporte guardado: {archivo_reporte}")
        logger.info(f"{'='*80}\n")
        
        return {
            'resultados_por_símbolo': todos_resultados,
            'alertas': alertas_consolidadas,
            'eventos': eventos_detectados_global,
            'tiempo_ejecución': tiempo_total,
            'archivo_gráfico': archivo_gráfico,
            'archivo_reporte': archivo_reporte,
        }


def main():
    """Función principal"""
    # Configurar logging
    setup_logging(log_level='INFO')
    
    # Crear analizador
    analizador = AnalisisInstPosiciones()
    
    # Ejecutar análisis completo
    resultados = analizador.ejecutar_análisis_completo()
    
    return resultados


if __name__ == "__main__":
    resultados = main()
