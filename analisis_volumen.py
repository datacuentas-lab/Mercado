import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import requests
from collections import defaultdict
import warnings
# Ignorar solo DeprecationWarnings, mantener otros warnings visibles
warnings.filterwarnings('ignore', category=DeprecationWarning)

class AdvancedOptionsAnalyzer:
    def __init__(self):
        # Definir símbolos por sector
        self.sectores = {
            'Indices': ['SPY', 'QQQ', 'IWM', 'DIA'],
            'Tecnologicas': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA'],
            'Energia': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC'],
            'Financieras': ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
            'Salud': ['JNJ', 'PFE', 'UNH', 'MRK', 'ABT']
        }
        
        # Fechas importantes (earnings, FOMC, etc.)
        self.eventos_importantes = self._cargar_eventos_calendario()
        
    def _cargar_eventos_calendario(self):
        """
        Carga fechas de eventos importantes (earnings, FOMC, etc.)
        """
        # En un entorno real, esto vendría de una API como Quandl, Alpha Vantage, etc.
        # Aquí incluimos eventos pasados y futuros para demostración
        eventos = {
            'earnings_season': [
                datetime(2025, 1, 15),  # Q4 2024
                datetime(2025, 4, 15),  # Q1 2025
                datetime(2025, 7, 15),  # Q2 2025
                datetime(2025, 10, 15), # Q3 2025
                datetime(2026, 1, 20),  # Q4 2025 (FUTURO)
                datetime(2026, 4, 15),  # Q1 2026 (FUTURO)
            ],
            'fomc_meetings': [
                datetime(2025, 1, 29),
                datetime(2025, 3, 19),
                datetime(2025, 5, 7),
                datetime(2025, 6, 18),
                datetime(2025, 7, 30),
                datetime(2025, 9, 17),
                datetime(2025, 11, 5),   # Muy reciente, posible
                datetime(2025, 12, 17),  # FUTURO
                datetime(2026, 1, 27),   # FUTURO
                datetime(2026, 3, 17),   # FUTURO
            ],
            'quad_witching': [  # Vencimientos importantes
                datetime(2025, 3, 21),
                datetime(2025, 6, 20),
                datetime(2025, 9, 19),
                datetime(2025, 12, 19),  # FUTURO
                datetime(2026, 3, 20),   # FUTURO
            ]
        }
        return eventos
    
    def obtener_datos_opciones_extendido(self, symbol, días_vencimiento=30, incluir_múltiples_exp=True):
        """
        Obtiene datos de opciones con información extendida de volumen
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Obtener precio actual del subyacente
            info = ticker.info
            precio_actual = info.get('currentPrice', info.get('regularMarketPrice', 0))
            
            # Validar que el precio sea válido
            if precio_actual <= 0:
                print(f"⚠️  Precio inválido para {symbol}: {precio_actual}")
                return None
            
            # Obtener fechas de vencimiento
            exp_dates = ticker.options
            if not exp_dates:
                return None
                
            datos_completos = []
            
            if incluir_múltiples_exp:
                # Analizar múltiples vencimientos para mejor análisis de volumen
                fechas_a_analizar = exp_dates[:3]  # Primeras 3 fechas
            else:
                # Solo la fecha más cercana al objetivo
                target_date = datetime.now() + timedelta(days=días_vencimiento)
                fechas_a_analizar = [min(exp_dates, 
                                       key=lambda x: abs(datetime.strptime(x, '%Y-%m-%d') - target_date))]
            
            for exp_date in fechas_a_analizar:
                # Obtener cadena de opciones
                opt_chain = ticker.option_chain(exp_date)
                
                # Procesar calls y puts
                calls = opt_chain.calls.copy()
                puts = opt_chain.puts.copy()
                
                calls['tipo'] = 'CALL'
                puts['tipo'] = 'PUT'
                
                # Combinar datos
                options_data = pd.concat([calls, puts], ignore_index=True)
                options_data['symbol'] = symbol
                options_data['expiration'] = exp_date
                options_data['precio_subyacente'] = precio_actual
                options_data['días_vencimiento'] = (datetime.strptime(exp_date, '%Y-%m-%d') - datetime.now()).days
                
                # Calcular moneyness
                options_data['moneyness'] = options_data['strike'] / precio_actual
                options_data['itm_otm'] = options_data.apply(
                    lambda x: 'ITM' if (x['tipo'] == 'CALL' and x['moneyness'] > 1) or 
                                     (x['tipo'] == 'PUT' and x['moneyness'] < 1) else 'OTM', axis=1
                )
                
                datos_completos.append(options_data)
            
            return pd.concat(datos_completos, ignore_index=True) if datos_completos else None
            
        except Exception as e:
            print(f"Error obteniendo datos para {symbol}: {e}")
            return None
    
    def analizar_volumen_detallado(self, df):
        """
        Análisis detallado del volumen de opciones
        """
        if df is None or df.empty:
            return None
            
        análisis = {}
        
        # === MÉTRICAS BÁSICAS DE VOLUMEN ===
        análisis['vol_total'] = df['volume'].sum()
        análisis['vol_calls'] = df[df['tipo'] == 'CALL']['volume'].sum()
        análisis['vol_puts'] = df[df['tipo'] == 'PUT']['volume'].sum()
        
        # Ratio Put/Call por volumen (más importante que por OI)
        análisis['vol_put_call_ratio'] = (análisis['vol_puts'] / análisis['vol_calls'] 
                                         if análisis['vol_calls'] > 0 else 0)
        
        # === ANÁLISIS DE CONCENTRACIÓN DE VOLUMEN ===
        # Volumen por strike
        vol_por_strike = df.groupby(['strike', 'tipo'])['volume'].sum().reset_index()
        análisis['strike_mayor_volumen'] = vol_por_strike.loc[vol_por_strike['volume'].idxmax()]
        
        # Volumen ITM vs OTM
        vol_itm = df[df['itm_otm'] == 'ITM']['volume'].sum()
        vol_otm = df[df['itm_otm'] == 'OTM']['volume'].sum()
        análisis['vol_itm'] = vol_itm
        análisis['vol_otm'] = vol_otm
        análisis['itm_otm_ratio'] = vol_itm / vol_otm if vol_otm > 0 else 0
        
        # === ANÁLISIS DE LIQUIDEZ ===
        # Relación Volumen/Open Interest (rotación) - Vectorizado
        df['vol_oi_individual'] = np.where(
            df['openInterest'] > 0, 
            df['volume'] / df['openInterest'], 
            0
        )
        análisis['rotación_promedio'] = df['vol_oi_individual'].mean()
        análisis['alta_rotación_count'] = len(df[df['vol_oi_individual'] > 1.0])  # Más volumen que OI
        
        # === ANÁLISIS POR VENCIMIENTO ===
        vol_por_vencimiento = df.groupby(['expiration', 'tipo'])['volume'].sum().reset_index()
        análisis['distribución_vencimientos'] = vol_por_vencimiento
        
        # === DETECCIÓN DE ACTIVIDAD INUSUAL ===
        # Contratos con volumen extremadamente alto
        q95_vol = df['volume'].quantile(0.95)
        contratos_alta_actividad = df[df['volume'] > q95_vol]
        análisis['contratos_alta_actividad'] = len(contratos_alta_actividad)
        análisis['vol_alta_actividad'] = contratos_alta_actividad['volume'].sum()
        
        # === MÉTRICAS DE SENTIMIENTO ===
        # Volumen ponderado por distancia al precio actual
        df['peso_distancia'] = 1 / (abs(df['moneyness'] - 1) + 0.01)  # Más peso cerca del dinero
        vol_calls_ponderado = (df[df['tipo'] == 'CALL']['volume'] * df[df['tipo'] == 'CALL']['peso_distancia']).sum()
        vol_puts_ponderado = (df[df['tipo'] == 'PUT']['volume'] * df[df['tipo'] == 'PUT']['peso_distancia']).sum()
        
        análisis['vol_put_call_ponderado'] = (vol_puts_ponderado / vol_calls_ponderado 
                                             if vol_calls_ponderado > 0 else 0)
        
        return análisis
    
    def detectar_eventos_próximos(self, symbol, días_adelante=90):
        """
        Detecta eventos importantes próximos que puedan afectar el volumen
        Parámetro días_adelante: número de días a buscar hacia el futuro (default: 90 días = 3 meses)
        """
        fecha_actual = datetime.now()
        fecha_límite = fecha_actual + timedelta(days=días_adelante)
        
        # Usar list comprehension en lugar de loops anidados
        eventos_próximos = [
            {
                'tipo': tipo_evento,
                'fecha': fecha,
                'días_restantes': (fecha - fecha_actual).days,
                'symbol': symbol
            }
            for tipo_evento, fechas in self.eventos_importantes.items()
            for fecha in fechas
            if fecha_actual <= fecha <= fecha_límite
        ]
        
        return eventos_próximos
    
    def analizar_volumen_pre_evento(self, resultados_sector):
        """
        Analiza patrones de volumen antes de eventos importantes
        (Recibe datos ya procesados del sector para evitar llamadas duplicadas a API)
        """
        análisis_eventos = {}
        
        for sector, df_sector in resultados_sector.items():
            if df_sector.empty:
                continue
                
            for _, row in df_sector.iterrows():
                symbol = row['symbol']
                eventos_próximos = self.detectar_eventos_próximos(symbol)
                
                if eventos_próximos:
                    # Los datos ya están procesados en resultados_sector
                    análisis_eventos[symbol] = {
                        'eventos_próximos': eventos_próximos,
                        'análisis_volumen': row.to_dict(),  # Convertir fila a dict
                        'sector': sector
                    }
        
        return análisis_eventos
    
    def generar_alertas_volumen(self, resultados_sector, análisis_eventos=None):
        """
        Genera alertas específicas basadas en patrones de volumen
        """
        alertas = []
        
        for sector, df in resultados_sector.items():
            if df.empty:
                continue
            
            for _, row in df.iterrows():
                symbol = row['symbol']
                
                # === ALERTA 1: Ratio Put/Call por volumen extremo ===
                if 'vol_put_call_ratio' in row and row['vol_put_call_ratio'] > 1.5:
                    alertas.append({
                        'tipo': 'VOLUMEN_PUTS_EXTREMO',
                        'prioridad': 'ALTA',
                        'sector': sector,
                        'symbol': symbol,
                        'valor': row['vol_put_call_ratio'],
                        'mensaje': f"🚨 {symbol}: Volumen PUT/CALL = {row['vol_put_call_ratio']:.2f} - Posible posicionamiento defensivo institucional"
                    })
                
                # === ALERTA 2: Alta rotación (Volumen >> Open Interest) ===
                if 'rotación_promedio' in row and row['rotación_promedio'] > 0.8:
                    alertas.append({
                        'tipo': 'ALTA_ROTACIÓN',
                        'prioridad': 'MEDIA',
                        'sector': sector,
                        'symbol': symbol,
                        'valor': row['rotación_promedio'],
                        'mensaje': f"📈 {symbol}: Alta rotación ({row['rotación_promedio']:.1%}) - Nueva actividad institucional"
                    })
                
                # === ALERTA 3: Volumen concentrado en pocos strikes ===
                if 'contratos_alta_actividad' in row and row['contratos_alta_actividad'] > 5:
                    alertas.append({
                        'tipo': 'CONCENTRACIÓN_VOLUMEN',
                        'prioridad': 'MEDIA',
                        'sector': sector,
                        'symbol': symbol,
                        'valor': row['contratos_alta_actividad'],
                        'mensaje': f"🎯 {symbol}: Volumen concentrado en {row['contratos_alta_actividad']} contratos específicos"
                    })
        
        # === ALERTAS POR EVENTOS PRÓXIMOS ===
        if análisis_eventos:
            for symbol, data in análisis_eventos.items():
                for evento in data['eventos_próximos']:
                    vol_ratio = data['análisis_volumen'].get('vol_put_call_ratio', 0)
                    
                    if vol_ratio > 1.2:  # Más volumen en puts antes del evento
                        alertas.append({
                            'tipo': 'PRE_EVENTO_DEFENSIVO',
                            'prioridad': 'ALTA',
                            'sector': data['sector'],
                            'symbol': symbol,
                            'evento': evento,
                            'valor': vol_ratio,
                            'mensaje': f"⚠️ {symbol}: Volumen defensivo antes de {evento['tipo']} ({evento['días_restantes']} días) - P/C = {vol_ratio:.2f}"
                        })
        
        # Ordenar alertas por prioridad
        orden_prioridad = {'ALTA': 1, 'MEDIA': 2, 'BAJA': 3}
        alertas.sort(key=lambda x: orden_prioridad.get(x['prioridad'], 999))
        
        return alertas
    
    def visualizar_análisis_volumen(self, resultados_sector, análisis_eventos=None):
        """
        Crea visualizaciones específicas del análisis de volumen
        """
        fig, axes = plt.subplots(2, 3, figsize=(20, 12))
        fig.suptitle('Análisis Avanzado de Volumen de Opciones', fontsize=16, fontweight='bold')
        
        # Combinar datos
        todos_datos = pd.concat([df for df in resultados_sector.values() if not df.empty], ignore_index=True)
        
        if todos_datos.empty:
            print("No hay datos para visualizar")
            return
        
        # === GRÁFICO 1: Volumen Put/Call Ratio por Sector ===
        if 'vol_put_call_ratio' in todos_datos.columns:
            vol_pcr_sector = todos_datos.groupby('sector')['vol_put_call_ratio'].mean().sort_values(ascending=True)
            bars1 = axes[0,0].barh(vol_pcr_sector.index, vol_pcr_sector.values, 
                                  color=['red' if x > 1.0 else 'green' for x in vol_pcr_sector.values])
            axes[0,0].set_title('Ratio Put/Call por Volumen - Por Sector')
            axes[0,0].set_xlabel('Put/Call Ratio (Volumen)')
            axes[0,0].axvline(x=1.0, color='black', linestyle='--', alpha=0.7, label='Neutralidad')
            axes[0,0].legend()
            
            # Añadir etiquetas de valor
            for i, (idx, val) in enumerate(vol_pcr_sector.items()):
                axes[0,0].text(val + 0.02, i, f'{val:.2f}', va='center')
        else:
            axes[0,0].text(0.5, 0.5, 'Datos de vol_put_call_ratio no disponibles',
                          ha='center', va='center', transform=axes[0,0].transAxes)
        
        # === GRÁFICO 2: Distribución de Rotación (Vol/OI) ===
        if 'rotación_promedio' in todos_datos.columns:
            axes[0,1].hist(todos_datos['rotación_promedio'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            axes[0,1].axvline(x=todos_datos['rotación_promedio'].mean(), color='red', linestyle='--', 
                             label=f'Media: {todos_datos["rotación_promedio"].mean():.2f}')
            axes[0,1].set_title('Distribución de Rotación (Volumen/OI)')
            axes[0,1].set_xlabel('Rotación')
            axes[0,1].set_ylabel('Frecuencia')
            axes[0,1].legend()
        
        # === GRÁFICO 3: Top Símbolos por Volumen Total ===
        if 'vol_total' in todos_datos.columns and len(todos_datos) > 0:
            n_top = min(10, len(todos_datos))
            top_vol = todos_datos.nlargest(n_top, 'vol_total')[['symbol', 'vol_total', 'sector']]
            colors = plt.cm.Set3(np.arange(len(top_vol)))
            bars3 = axes[0,2].bar(range(len(top_vol)), top_vol['vol_total'], color=colors)
            axes[0,2].set_title(f'Top {n_top} Símbolos por Volumen Total')
            axes[0,2].set_ylabel('Volumen Total')
            axes[0,2].set_xticks(range(len(top_vol)))
            axes[0,2].set_xticklabels(top_vol['symbol'], rotation=45)
        else:
            axes[0,2].text(0.5, 0.5, 'Datos de volumen no disponibles',
                          ha='center', va='center', transform=axes[0,2].transAxes)
        
        # === GRÁFICO 4: Heatmap de Métricas de Volumen por Sector ===
        métricas_vol = ['vol_put_call_ratio', 'rotación_promedio']
        métricas_disponibles = [m for m in métricas_vol if m in todos_datos.columns]
        
        if métricas_disponibles:
            datos_heatmap = todos_datos.groupby('sector')[métricas_disponibles].mean()
            im = axes[1,0].imshow(datos_heatmap.T, cmap='RdYlBu_r', aspect='auto')
            axes[1,0].set_xticks(range(len(datos_heatmap.index)))
            axes[1,0].set_xticklabels(datos_heatmap.index, rotation=45)
            axes[1,0].set_yticks(range(len(métricas_disponibles)))
            axes[1,0].set_yticklabels(métricas_disponibles)
            axes[1,0].set_title('Heatmap: Métricas de Volumen por Sector')
            plt.colorbar(im, ax=axes[1,0])
        
        # === GRÁFICO 5: Análisis Pre-Eventos ===
        if análisis_eventos:
            eventos_data = []
            for symbol, data in análisis_eventos.items():
                for evento in data['eventos_próximos']:
                    eventos_data.append({
                        'symbol': symbol,
                        'días_evento': evento['días_restantes'],
                        'vol_pcr': data['análisis_volumen'].get('vol_put_call_ratio', 0),
                        'tipo_evento': evento['tipo'],
                        'sector': data['sector']
                    })
            
            if eventos_data:
                df_eventos = pd.DataFrame(eventos_data)
                
                # Crear scatter plot con colores por tipo de evento
                tipos_evento = df_eventos['tipo_evento'].unique()
                colors = plt.cm.tab10(np.arange(len(tipos_evento)))
                
                for i, tipo in enumerate(tipos_evento):
                    data_tipo = df_eventos[df_eventos['tipo_evento'] == tipo]
                    scatter = axes[1,1].scatter(data_tipo['días_evento'], data_tipo['vol_pcr'], 
                                              c=colors[i], s=100, alpha=0.7, label=tipo)
                
                axes[1,1].set_xlabel('Días hasta Evento')
                axes[1,1].set_ylabel('Put/Call Ratio (Volumen)')
                axes[1,1].set_title('Volumen Pre-Eventos: Posicionamiento Defensivo')
                axes[1,1].axhline(y=1.2, color='red', linestyle='--', alpha=0.7, label='Umbral Defensivo')
                axes[1,1].legend()
                axes[1,1].grid(True, alpha=0.3)
                
                # Añadir anotaciones para puntos importantes
                for _, row in df_eventos.iterrows():
                    if row['vol_pcr'] > 1.5:  # Casos muy defensivos
                        axes[1,1].annotate(row['symbol'], 
                                         (row['días_evento'], row['vol_pcr']),
                                         xytext=(5, 5), textcoords='offset points',
                                         fontsize=8, alpha=0.8)
        else:
            axes[1,1].text(0.5, 0.5, 'No hay eventos próximos\nen el período analizado', 
                          ha='center', va='center', transform=axes[1,1].transAxes, 
                          fontsize=12, style='italic')
            axes[1,1].set_title('Análisis Pre-Eventos')
        
        # === GRÁFICO 6: Volumen Intradía vs Promedio ===
        if 'vol_total' in todos_datos.columns:
            # Comparar volumen actual vs promedio histórico (usando ratio fijo)
            # En producción, esto vendría de una base de datos histórica
            todos_datos['vol_promedio_simulado'] = todos_datos['vol_total'] * 0.85  # Promedio típico 85% del actual
            todos_datos['vol_ratio_vs_promedio'] = todos_datos['vol_total'] / (todos_datos['vol_promedio_simulado'] + 1e-6)
            
            # Scatter plot: volumen actual vs ratio de volumen inusual
            scatter6 = axes[1,2].scatter(todos_datos['vol_total'], todos_datos['vol_ratio_vs_promedio'],
                                       c=todos_datos['vol_put_call_ratio'], cmap='RdYlGn_r', 
                                       s=60, alpha=0.7)
            
            axes[1,2].set_xlabel('Volumen Total')
            axes[1,2].set_ylabel('Ratio vs Promedio Histórico')
            axes[1,2].set_title('Volumen Actual vs Histórico')
            axes[1,2].axhline(y=1.5, color='red', linestyle='--', alpha=0.7, label='Umbral Alto')
            axes[1,2].legend()
            
            # Colorbar para el ratio put/call
            cbar = plt.colorbar(scatter6, ax=axes[1,2])
            cbar.set_label('Put/Call Ratio', rotation=270, labelpad=15)
        
        plt.tight_layout()
        
        # Guardar gráfico como imagen
        nombre_archivo = 'analisis_volumen_opciones.png'
        plt.savefig(nombre_archivo, dpi=100, bbox_inches='tight')
        print(f"\n✓ Gráfico guardado como: {nombre_archivo}")
        
        plt.show()


# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("ANÁLISIS AVANZADO DE VOLUMEN DE OPCIONES")
    print("=" * 80)
    
    # Inicializar analizador
    analyzer = AdvancedOptionsAnalyzer()
    print("\n✓ Analizador inicializado")
    
    # Recopilar datos por sector
    print("\n📊 Recopilando datos de opciones...")
    resultados_sector = {}
    
    for sector, symbols in analyzer.sectores.items():
        print(f"\n  Procesando sector: {sector}")
        datos_sector = []
        
        for symbol in symbols:
            print(f"    → {symbol}...", end=' ', flush=True)
            datos = analyzer.obtener_datos_opciones_extendido(symbol)
            
            if datos is not None:
                análisis = analyzer.analizar_volumen_detallado(datos)
                if análisis:
                    fila = {'symbol': symbol, 'sector': sector}
                    fila.update(análisis)
                    datos_sector.append(fila)
                    print("✓")
                else:
                    print("✗ (análisis vacío)")
            else:
                print("✗ (sin datos)")
        
        if datos_sector:
            resultados_sector[sector] = pd.DataFrame(datos_sector)
            print(f"    ✓ {len(datos_sector)} símbolos procesados")
        else:
            resultados_sector[sector] = pd.DataFrame()
    
    # Análisis pre-eventos
    print("\n📅 Analizando volumen pre-eventos...")
    análisis_eventos = analyzer.analizar_volumen_pre_evento(resultados_sector)
    print(f"   ✓ {len(análisis_eventos)} símbolos con eventos próximos")
    
    # Generar alertas
    print("\n🚨 Generando alertas...")
    alertas = analyzer.generar_alertas_volumen(resultados_sector, análisis_eventos)
    print(f"   ✓ {len(alertas)} alertas generadas")
    
    if alertas:
        print("\n" + "=" * 80)
        print("ALERTAS GENERADAS")
        print("=" * 80)
        for i, alerta in enumerate(alertas, 1):
            print(f"\n{i}. {alerta['mensaje']}")
            print(f"   Prioridad: {alerta['prioridad']} | Sector: {alerta['sector']}")
    
    # Generar visualizaciones
    print("\n📈 Generando visualizaciones...")
    analyzer.visualizar_análisis_volumen(resultados_sector, análisis_eventos)
    
    print("\n" + "=" * 80)
    print("✓ ANÁLISIS COMPLETADO")
    print("=" * 80)     