"""
Generación de reportes y visualizaciones
"""

from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path

from ..utils import ordenar_alertas_por_prioridad


logger = logging.getLogger(__name__)


class ReportGenerator:
    """Genera reportes y visualizaciones de análisis"""
    
    def __init__(self, output_dir: str = "reportes"):
        """
        Inicializa el generador de reportes
        
        Args:
            output_dir: Directorio donde guardar reportes
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Configurar estilo
        sns.set_style("darkgrid")
        plt.rcParams['figure.figsize'] = (16, 12)
        plt.rcParams['font.size'] = 9
        
    def consolidar_alertas(self, análisis_resultados: Dict) -> List[Dict]:
        """
        Consolida alertas de múltiples analizadores
        
        Args:
            análisis_resultados: Diccionario con resultados de análisis
                {símbolo: {analizer_name: {alerts: [...], metrics: {...}}}}
        
        Returns:
            Lista consolidada y ordenada de alertas
        """
        alertas_consolidadas = []
        
        for símbolo, resultados_símbolo in análisis_resultados.items():
            for analyzer_name, resultado in resultados_símbolo.items():
                if 'alerts' in resultado:
                    for alerta in resultado['alerts']:
                        alerta_completa = {
                            'símbolo': símbolo,
                            'analizador': analyzer_name,
                            **alerta
                        }
                        alertas_consolidadas.append(alerta_completa)
        
        # Ordenar por prioridad
        return ordenar_alertas_por_prioridad(alertas_consolidadas)
    
    def generar_alertas_volumen(self, alertas: List[Dict]) -> str:
        """
        Genera reporte de alertas en formato texto
        
        Args:
            alertas: Lista de alertas
            
        Returns:
            Reporte en formato texto
        """
        if not alertas:
            return "No hay alertas generadas."
        
        # Agrupar por prioridad
        alertas_por_prioridad = {}
        for alerta in alertas:
            prioridad = alerta.get('prioridad', 'BAJA')
            if prioridad not in alertas_por_prioridad:
                alertas_por_prioridad[prioridad] = []
            alertas_por_prioridad[prioridad].append(alerta)
        
        reporte = f"\n{'='*80}\n"
        reporte += f"REPORTE DE ALERTAS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        reporte += f"{'='*80}\n\n"
        
        orden_prioridades = ['ALTA', 'MEDIA', 'BAJA']
        total_alertas = 0
        
        for prioridad in orden_prioridades:
            if prioridad in alertas_por_prioridad:
                alertas_prioridad = alertas_por_prioridad[prioridad]
                total_alertas += len(alertas_prioridad)
                
                reporte += f"\n{prioridad} PRIORIDAD ({len(alertas_prioridad)} alertas):\n"
                reporte += "-" * 80 + "\n"
                
                for i, alerta in enumerate(alertas_prioridad, 1):
                    reporte += f"\n{i}. [{alerta.get('símbolo', 'N/A')}] {alerta.get('analizador', 'N/A')}\n"
                    reporte += f"   Tipo: {alerta.get('tipo', 'N/A')}\n"
                    reporte += f"   Descripción: {alerta.get('descripción', 'N/A')}\n"
                    if 'valor' in alerta:
                        reporte += f"   Valor: {alerta['valor']:.2f}\n"
                    if 'umbral' in alerta:
                        reporte += f"   Umbral: {alerta['umbral']:.2f}\n"
        
        reporte += f"\n{'='*80}\n"
        reporte += f"TOTAL ALERTAS: {total_alertas}\n"
        reporte += f"{'='*80}\n"
        
        return reporte
    
    def visualizar_análisis_volumen(
        self,
        análisis_resultados: Dict,
        eventos_detectados: Optional[Dict] = None,
        nombre_archivo: str = "análisis_volumen.png"
    ) -> str:
        """
        Crea visualización con múltiples gráficos
        
        Args:
            análisis_resultados: Resultados de análisis por símbolo
            eventos_detectados: Eventos detectados
            nombre_archivo: Nombre del archivo a guardar
            
        Returns:
            Ruta del archivo guardado
        """
        fig = plt.figure(figsize=(16, 12))
        
        # Gráfico 1: Distribución de PCR ratios (Volumen)
        ax1 = plt.subplot(3, 2, 1)
        pcr_valores = []
        símbolos = []
        for símbolo, resultados in análisis_resultados.items():
            if 'volume_analyzer' in resultados and 'metrics' in resultados['volume_analyzer']:
                pcr = resultados['volume_analyzer']['metrics'].get('vol_put_call_ratio', 0)
                # Filtrar valores válidos (no NaN, no infinito, mayor que 0)
                if isinstance(pcr, (int, float)) and not pd.isna(pcr) and not np.isinf(pcr) and pcr > 0:
                    pcr_valores.append(pcr)
                    símbolos.append(símbolo)
        
        if pcr_valores:
            # Ordenar por valor PCR descendente para mostrar los más altos
            sorted_indices = sorted(range(len(pcr_valores)), key=lambda i: pcr_valores[i], reverse=True)
            símbolos_sorted = [símbolos[i] for i in sorted_indices[:10]]
            pcr_sorted = [pcr_valores[i] for i in sorted_indices[:10]]
            
            ax1.barh(símbolos_sorted, pcr_sorted, color='steelblue')
            ax1.axvline(x=1.0, color='red', linestyle='--', label='Umbral (1.0)')
            ax1.set_xlabel('PCR Ratio')
            ax1.set_title('Top 10: Put/Call Ratio (Volumen)', fontweight='bold')
            ax1.legend()
        else:
            ax1.text(0.5, 0.5, 'No hay datos de PCR\npara volumen', ha='center', va='center')
            ax1.set_title('Put/Call Ratio (Volumen)', fontweight='bold')
        
        # Gráfico 2: Distribución de PCR ratios (OI)
        ax2 = plt.subplot(3, 2, 2)
        pcr_oi_valores = []
        símbolos_oi = []
        for símbolo, resultados in análisis_resultados.items():
            if 'open_interest_analyzer' in resultados and 'metrics' in resultados['open_interest_analyzer']:
                pcr = resultados['open_interest_analyzer']['metrics'].get('oi_put_call_ratio', 0)
                # Filtrar valores válidos (no NaN, no infinito, mayor que 0)
                if isinstance(pcr, (int, float)) and not pd.isna(pcr) and not np.isinf(pcr) and pcr > 0:
                    pcr_oi_valores.append(pcr)
                    símbolos_oi.append(símbolo)
        
        if pcr_oi_valores:
            # Ordenar por valor PCR descendente para mostrar los más altos
            sorted_indices = sorted(range(len(pcr_oi_valores)), key=lambda i: pcr_oi_valores[i], reverse=True)
            símbolos_sorted = [símbolos_oi[i] for i in sorted_indices[:10]]
            pcr_sorted = [pcr_oi_valores[i] for i in sorted_indices[:10]]
            
            ax2.barh(símbolos_sorted, pcr_sorted, color='coral')
            ax2.axvline(x=1.0, color='red', linestyle='--', label='Umbral (1.0)')
            ax2.set_xlabel('PCR Ratio')
            ax2.set_title('Top 10: Put/Call Ratio (Open Interest)', fontweight='bold')
            ax2.legend()
        else:
            ax2.text(0.5, 0.5, 'No hay datos de PCR\npara Open Interest', ha='center', va='center')
            ax2.set_title('Put/Call Ratio (Open Interest)', fontweight='bold')
        
        # Gráfico 3: Conteo de alertas por prioridad
        ax3 = plt.subplot(3, 2, 3)
        alertas = self.consolidar_alertas(análisis_resultados)
        conteos = {'ALTA': 0, 'MEDIA': 0, 'BAJA': 0}
        for alerta in alertas:
            prioridad = alerta.get('prioridad', 'BAJA')
            if prioridad in conteos:
                conteos[prioridad] += 1
        
        colores = ['red', 'orange', 'yellow']
        ax3.bar(conteos.keys(), conteos.values(), color=colores)
        ax3.set_ylabel('Cantidad')
        ax3.set_title('Distribución de Alertas por Prioridad', fontweight='bold')
        for i, (k, v) in enumerate(conteos.items()):
            ax3.text(i, v + 1, str(v), ha='center', fontweight='bold')
        
        # Gráfico 4: Análisis de rotación (Vol/OI)
        ax4 = plt.subplot(3, 2, 4)
        rotación_valores = []
        símbolos_rot = []
        for símbolo, resultados in análisis_resultados.items():
            if 'volume_analyzer' in resultados and 'metrics' in resultados['volume_analyzer']:
                rot = resultados['volume_analyzer']['metrics'].get('rotación_promedio', 0)
                # Filtrar valores válidos (no NaN, no infinito, mayor que 0)
                if isinstance(rot, (int, float)) and not pd.isna(rot) and not np.isinf(rot) and rot > 0:
                    rotación_valores.append(rot)
                    símbolos_rot.append(símbolo)
        
        if rotación_valores:
            # Ordenar por valor de rotación descendente para mostrar los más altos
            sorted_indices = sorted(range(len(rotación_valores)), key=lambda i: rotación_valores[i], reverse=True)
            símbolos_sorted = [símbolos_rot[i] for i in sorted_indices[:10]]
            rot_sorted = [rotación_valores[i] for i in sorted_indices[:10]]
            
            ax4.barh(símbolos_sorted, rot_sorted, color='green')
            ax4.set_xlabel('Rotación (Vol/OI)')
            ax4.set_title('Top 10: Rotación de Volumen', fontweight='bold')
        else:
            ax4.text(0.5, 0.5, 'No hay datos de\nrotación válidos', ha='center', va='center')
            ax4.set_title('Rotación de Volumen', fontweight='bold')
        
        # Gráfico 5: Símbolos con eventos próximos
        ax5 = plt.subplot(3, 2, 5)
        if eventos_detectados:
            # Agrupar eventos por sector en lugar de por símbolo
            eventos_por_sector = {}
            for evento in eventos_detectados:
                sector = evento.get('sector', 'Unknown')
                if sector not in eventos_por_sector:
                    eventos_por_sector[sector] = 0
                eventos_por_sector[sector] += 1
            
            if eventos_por_sector:
                # Ordenar por cantidad de eventos descendente
                sectores_ordenados = dict(sorted(
                    eventos_por_sector.items(),
                    key=lambda x: x[1],
                    reverse=True
                ))
                
                ax5.barh(list(sectores_ordenados.keys()), list(sectores_ordenados.values()), color='purple')
                ax5.set_xlabel('Cantidad de Eventos')
                ax5.set_title(f'Sectores con Eventos Próximos (Total: {len(eventos_detectados)})', fontweight='bold')
                # Agregar etiquetas con los valores
                for i, (sector, count) in enumerate(sectores_ordenados.items()):
                    ax5.text(count + 0.5, i, str(count), va='center', fontweight='bold')
            else:
                ax5.text(0.5, 0.5, 'No hay eventos por sector', ha='center', va='center')
                ax5.set_title('Sectores con Eventos Próximos', fontweight='bold')
        else:
            ax5.text(0.5, 0.5, 'No hay eventos detectados', ha='center', va='center')
            ax5.set_title('Sectores con Eventos Próximos', fontweight='bold')
        
        # Gráfico 6: Resumen de métricas
        ax6 = plt.subplot(3, 2, 6)
        ax6.axis('off')
        
        # Información resumida
        resumen_text = f"""
RESUMEN DE ANÁLISIS
{'-'*40}
Símbolos analizados: {len(análisis_resultados)}
Total alertas: {len(alertas)}
Alertas ALTA: {conteos['ALTA']}
Alertas MEDIA: {conteos['MEDIA']}
Alertas BAJA: {conteos['BAJA']}
Eventos detectados: {len(eventos_detectados) if eventos_detectados else 0}
Fecha análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        ax6.text(0.1, 0.9, resumen_text, transform=ax6.transAxes, 
                fontsize=10, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # Guardar archivo
        archivo_salida = self.output_dir / nombre_archivo
        plt.savefig(archivo_salida, dpi=100, bbox_inches='tight')
        logger.info(f"Gráfico guardado en: {archivo_salida}")
        plt.close()
        
        return str(archivo_salida)
    
    def guardar_reporte_texto(self, contenido: str, nombre_archivo: str = "reporte.txt") -> str:
        """
        Guarda reporte en archivo de texto
        
        Args:
            contenido: Contenido del reporte
            nombre_archivo: Nombre del archivo
            
        Returns:
            Ruta del archivo guardado
        """
        archivo_salida = self.output_dir / nombre_archivo
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            f.write(contenido)
        logger.info(f"Reporte guardado en: {archivo_salida}")
        return str(archivo_salida)
