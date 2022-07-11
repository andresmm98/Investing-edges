#------------------------------------------------------------------------------
# EL PROGRAMA HACE EL BACKTESTING DE UNA ESTRATEGIA 
#
# Tiene 3 clases: 
# 1. strategy: sin métodos de momento
# 2. backtesting: un método para dividir los datos en cuantiles y otro para hacer el backtest
# 3. portfolio: un método para rebalancearlo y otro para actualizar su precio
# 
# Al programa de nuestra base de datos lo he llamado market_data.
# Si haces control + f con 'market_data' puedes encontrar los métodos que necesitamos que tenga ese programa 
# con comentarios explicativos.
#
# Falta añadir muchas métricas y graficarlas. De momento solo hay una variable {performance} en cada portfolio 
# que guarda una lista de tuplas con fechas y el valor de la cartera en ese día. A partir de ahí ya se podría 
# graficar el rendimiento y hacer pruebas.
# 
#------------------------------------------------------------------------------

import market_data # esta sería nuestro programa que nos da los datos a partir de la API
import numpy as np
import matplotlib as plt
import pandas as pd
from datetime import datetime, timedelta

class strategy(object):

    def __init__(self,
                factor='volume',
                less_is_better=True):

        self.factor = factor # el factor a estudiar, de momento solo puede ser uno       
        self.less_is_better = less_is_better # para ordenar las acciones por orden ascendente o descendente

class backtesting(object):

    def __init__(self, 
                strategy=strategy(),
                quantiles=10,
                market='NYSE',
                start_date='1988-03-09',
                check_period=30,
                rebalance_period=90,
                budget=100000):

        self.strategy = strategy
        self.quantiles = quantiles
        self.market = market
        self.start_date = start_date
        self.check_period = check_period # Periodo para actualizar el valor de la cartera. De momento debe estar en días
        self.rebalance_period = rebalance_period # Debe ser un múltiplo de {check_period}
        self.budget = budget # presupuesto por portfolio
    
    def create_quantiles(self, date):
        ''' Divide el dataframe en X cuantiles según el factor deseado 
        
        Cada cuantil es una lista de tuplas (ticker, precio de apertura).
        Se utiliza para construir las carteras.'''
        
        # Constructor del dataframe. Se espera obtener un objeto con:
        # - tantas filas como acciones coticen en ese mercado y fecha
        # - 3 columnas de nombre "symbol", "factor" y "open"
        # "close" es solamente el precio de cierre en esa fecha

        stocks_df = market_data.create_dataframe(self.strategy.factor, self.market, date)
        
        stocks_df.sort_values(by=self.factor, ascending=self.less_is_better)

        n_stocks = len(stocks_df.index)
        stocks_per_quantile = int(n_stocks/self.quantiles)
        
        # Como la división de acciones por cuantil no será siempre entera, ponemos una acción más en los primeros cuantiles hasta que el resto sea 0
        remainder = n_stocks % self.quantiles
        split_indexes = []
        for i in range(self.quantiles):
            if i < remainder:
                split_indexes.append(stocks_per_quantile + i + 1)
            else:
                split_indexes.append(stocks_per_quantile + remainder)

        # Divide el datafrme en {quantiles} y los mete en una lista
        quantile_list = np.split(stocks_df, split_indexes)

        return quantile_list

    def backtest(self):
        ''' Hace el backtesting de la estrategia dada 
        
        La lógica de la función es la siguiente:
        1. Calculamos cuantas veces hay que mirar el valor de la cartera en cada rebalanceo
        2. Vamos sumando días a la fecha hasta que toca rebalancear, y cuando llegamos a la fecha actual paramos
        
        Los cuantiles vuelven a calcularse para cada nuevo rebalanceo'''
        
        date = datetime.strptime(self.start_date, '%Y-%m-%d')
        n_checks = self.rebalance_period / self.check_period
 
        # initialize portfolios
        portfolio_list = []
        for i in range(self.quantiles):
            portfolio_list.append(portfolio(self))

        while date < datetime.today():
            # rebalance portfolios
            quantile_list = create_quantiles(date.strftime('%Y-%m-%d'))
            for i in range(self.quantiles):
                portfolio_list[i] = build_portfolio(quantile_list[i], date.strftime('%Y-%m-%d'))
            
            # update performance
            for i in range(n_checks):
                date += timedelta(self.check_period)
                for i in range(self.quantiles):
                    compute_performance(portfolio_list[i], date.strftime('%Y-%m-%d'))
        
        return portfolio_list
        # falta el código para mostrar los resultados
            
class portfolio():

    def __init__(self, backtesting):

        self.positions = []
        self.backtesting = backtesting
        self.curr_value = backtesting.budget # valor monetario de la cartera. Al principio es el presupuesto inicial
        self.rebalanced_date = backtesting.start_date # fecha del último rebalanceo. La primera es la fecha de inicio
        self.perfomance = [(self.rebalanced_date, self.curr_value)] # lista de tuplas con fecha y valor

    def build_portfolio(self, quantile, date=backtesting.start_date):
        ''' Dado un cuantil de acciones se construye un portfolio para el presupuesto actual.
        El presupuesto se divide por igual entre todas las acciones.'''

        self.positions.clear() # reiniciamos el portfolio
        
        tickers = quantile['symbol']
        prices = quantile['open']
        
        n_stocks = len(tickers)
        
        money_per_stock = self.curr_value / n_stocks

        for i in range(n_stocks):
            position = money_per_stock / prices[i]
            self.positions.append((tickers[i], float(f'(position:4f)'))) # cada posición tiene 4 decimales, ignoramos el error de truncamiento

        self.rebalanced_date = date # fecha del último rebalanceo
        
        return self

    def compute_performance(self, date):
        ''' De momento solo calcula el valor de un portfolio para una fecha X '''

        portfolio_value = 0
        tickers = (i for i, j in self.positions)
        shares = (j for i, j in self.positions)
        
        # Se espera una lista con los precios de cierre del día anterior. Si la acción ha sido deslistada debe devolver None
        prices = market_data.get_prices(tickers, date)

        for i in range(len(tickers)):
            # suma el valor actual de las posiciones
            if prices[i] is not None:
                portfolio_value += shares[i] * prices[i]
            else:
                portfolio_value += shares[i] * market_data.get_delisting_price[tickers[i]] # buscar el precio en fecha de delisting

            # suma los dividendos pagados
            portfolio_value += market_data.get_paid_dividends(tickers[i], date - self.backtesting.check_period, date) # debe calcular los dividendos pagados por una lista de acciones entre dos fechas

        self.curr_value = portfolio_value
        self.performance.append(date, self.curr_value)

        return self
    
def main():
    with backtesting() as factor:
        factor.backtest()

if __name__ == '__main__':
    main()