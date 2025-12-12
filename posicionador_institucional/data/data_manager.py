"""
Gestor centralizado de datos de yfinance
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging

from ..models import OptionsChain

logger = logging.getLogger(__name__)


class DataManager:
    """Gestiona la obtención y procesamiento de datos de yfinance con caché eficiente"""
    
    def __init__(self):
        """Inicializar el gestor de datos"""
        # Cache de datos opciones: {symbol: {num_vencimientos: DataFrame}}
        self.opciones_cache = {}
        # Cache de precios: {symbol: (precio, timestamp)}
        self.precios_cache = {}
        # Cache de vencimientos disponibles: {symbol: [fechas]}
        self.vencimientos_cache = {}
    
    def obtener_datos_opciones(
        self, 
        symbol: str, 
        num_vencimientos: int = 3,
        include_moneyness: bool = True,
        usar_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Obtiene datos de opciones completos para un símbolo
        Con caché para evitar descargas repetidas
        
        Args:
            symbol: Símbolo a analizar
            num_vencimientos: Número de vencimientos a obtener
            include_moneyness: Si incluir cálculo de moneyness
            usar_cache: Si usar caché (True por defecto)
            
        Returns:
            DataFrame con datos de opciones combinados o None si hay error
        """
        # Verificar caché
        cache_key = f"{symbol}_{num_vencimientos}"
        if usar_cache and cache_key in self.opciones_cache:
            logger.debug(f"Usando caché para {symbol}")
            return self.opciones_cache[cache_key].copy()
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Obtener precio actual (usar caché si disponible)
            precio_actual = self._obtener_precio_cached(symbol, ticker)
            if precio_actual <= 0:
                logger.warning(f"Precio inválido para {symbol}: {precio_actual}")
                return None
            
            # Obtener fechas de vencimiento (usar caché)
            exp_dates = self._obtener_vencimientos_cached(symbol, ticker)
            if not exp_dates:
                logger.warning(f"No hay opciones disponibles para {symbol}")
                return None
            
            # Seleccionar vencimientos a analizar
            fechas_a_analizar = exp_dates[:min(num_vencimientos, len(exp_dates))]
            
            datos_completos = []
            
            for exp_date in fechas_a_analizar:
                opt_chain = ticker.option_chain(exp_date)
                
                # Procesar calls y puts
                calls = opt_chain.calls.copy()
                puts = opt_chain.puts.copy()
                
                calls['tipo'] = 'CALL'
                puts['tipo'] = 'PUT'
                
                # Combinar
                options_data = pd.concat([calls, puts], ignore_index=True)
                options_data['symbol'] = symbol
                options_data['expiration'] = exp_date
                options_data['precio_subyacente'] = precio_actual
                options_data['días_vencimiento'] = (
                    datetime.strptime(exp_date, '%Y-%m-%d') - datetime.now()
                ).days
                
                # Calcular moneyness si es requerido
                if include_moneyness:
                    options_data['moneyness'] = options_data['strike'] / precio_actual
                    options_data['itm_otm'] = options_data.apply(
                        lambda x: 'ITM' if (
                            (x['tipo'] == 'CALL' and x['moneyness'] > 1) or 
                            (x['tipo'] == 'PUT' and x['moneyness'] < 1)
                        ) else 'OTM',
                        axis=1
                    )
                
                datos_completos.append(options_data)
            
            if datos_completos:
                resultado = pd.concat(datos_completos, ignore_index=True)
                # Guardar en caché
                self.opciones_cache[cache_key] = resultado.copy()
                logger.info(f"Datos obtenidos y cacheados para {symbol} ({len(resultado)} filas)")
                return resultado
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol}: {e}")
            return None
    
    def _obtener_precio_cached(self, symbol: str, ticker) -> float:
        """Obtiene precio actual con caché (5 minutos)"""
        if symbol in self.precios_cache:
            precio, timestamp = self.precios_cache[symbol]
            if (datetime.now() - timestamp).total_seconds() < 300:  # 5 min
                logger.debug(f"Precio en caché para {symbol}")
                return precio
        
        try:
            info = ticker.info
            precio = info.get('currentPrice', info.get('regularMarketPrice', 0))
            self.precios_cache[symbol] = (precio, datetime.now())
            return precio
        except Exception as e:
            logger.error(f"Error obteniendo precio para {symbol}: {e}")
            return 0
    
    def _obtener_vencimientos_cached(self, symbol: str, ticker) -> List[str]:
        """Obtiene vencimientos disponibles con caché (10 minutos)"""
        if symbol in self.vencimientos_cache:
            exp_dates, timestamp = self.vencimientos_cache[symbol]
            if (datetime.now() - timestamp).total_seconds() < 600:  # 10 min
                logger.debug(f"Vencimientos en caché para {symbol}")
                return exp_dates
        
        try:
            exp_dates = ticker.options
            if exp_dates:
                self.vencimientos_cache[symbol] = (exp_dates, datetime.now())
                return exp_dates
            return []
        except Exception as e:
            logger.error(f"Error obteniendo vencimientos para {symbol}: {e}")
            return []
    
    def obtener_precio_actual(self, symbol: str) -> Optional[float]:
        """Obtiene el precio actual de un símbolo"""
        try:
            ticker = yf.Ticker(symbol)
            precio = self._obtener_precio_cached(symbol, ticker)
            return precio if precio > 0 else None
        except Exception as e:
            logger.error(f"Error obteniendo precio para {symbol}: {e}")
            return None
    
    def limpiar_cache(self, symbol: str = None):
        """
        Limpia el caché de datos
        
        Args:
            symbol: Si se proporciona, solo limpia datos de ese símbolo
        """
        if symbol:
            # Limpiar caché específico
            keys_to_remove = [k for k in self.opciones_cache.keys() if k.startswith(symbol)]
            for key in keys_to_remove:
                del self.opciones_cache[key]
            if symbol in self.precios_cache:
                del self.precios_cache[symbol]
            if symbol in self.vencimientos_cache:
                del self.vencimientos_cache[symbol]
            logger.info(f"Caché limpiado para {symbol}")
        else:
            # Limpiar todo
            self.opciones_cache.clear()
            self.precios_cache.clear()
            self.vencimientos_cache.clear()
            logger.info("Caché completamente limpiado")
    
    def obtener_estadisticas_cache(self) -> Dict:
        """Retorna estadísticas del caché actual"""
        return {
            'opciones_cacheadas': len(self.opciones_cache),
            'precios_cacheados': len(self.precios_cache),
            'vencimientos_cacheados': len(self.vencimientos_cache),
            'tamanio_opciones_kb': sum(df.memory_usage(deep=True).sum() / 1024 
                                       for df in self.opciones_cache.values())
        }
