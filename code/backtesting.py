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
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
import logging

class strategy(object):

    def __init__(self,
                factor='volume',
                less_is_better=True):

        self.factor = factor # el factor a estudiar, de momento solo puede ser uno       
        self.less_is_better = less_is_better # para ordenar las acciones por orden ascendente o descendente

    def __enter__(self):
        """ Entering a with statement """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """ Exiting a with statement """
        if traceback is not None:
            logging.error("Stopping with exception %s" % traceback)
    
    def create_quantiles(self, market_data, n_quantiles, date):
        ''' Divide el dataframe en X cuantiles según el factor deseado 
        
        Cada cuantil es una lista de tuplas (ticker, precio de apertura).
        Se utiliza para construir las carteras.'''
        
        # Constructor del dataframe. Se espera obtener un objeto con:
        # - tantas filas como acciones coticen en ese mercado y fecha
        # - 3 columnas de nombre "symbol", "factor" y "open"
        # "close" es solamente el precio de cierre en esa fecha

        stocks_df = market_data.get(date, ['open', self.factor])
        
        stocks_df.sort_values(by=self.factor, ascending=self.less_is_better)

        n_stocks = len(stocks_df.index)
        stocks_per_quantile = int(n_stocks/n_quantiles)
        
        # Como la división de acciones por cuantil no será siempre entera, ponemos una acción más en los primeros cuantiles hasta que el resto sea 0
        remainder = n_stocks % n_quantiles
        split_indexes = []
        index = 0
        for i in range(n_quantiles-1):
            if i < remainder:
                index += stocks_per_quantile + 1
            else:
                index += stocks_per_quantile 
            split_indexes.append(index)

        # Divide el datafrme en {quantiles} y los mete en una lista
        quantile_list = np.split(stocks_df, split_indexes)

        return quantile_list
    
    def backtest(self, 
                n_quantiles=4,
                market='NYSE',
                n_stocks=200,
                start_date='2019-03-09',
                check_period=30, # Periodo para actualizar el valor de la cartera. De momento debe estar en días
                rebalance_period=90, # Debe ser un múltiplo de {check_period}
                budget=100000): # presupuesto por portfolio
        
        ''' Hace el backtesting de la estrategia dada 
        
        La lógica de la función es la siguiente:
        1. Calculamos cuantas veces hay que mirar el valor de la cartera en cada rebalanceo
        2. Vamos sumando días a la fecha hasta que toca rebalancear, y cuando llegamos a la fecha actual paramos
        
        Los cuantiles vuelven a calcularse para cada nuevo rebalanceo'''
        
        logging.debug("Importing market data...")
        mk = market_data.market_data(market, n_stocks)
        logging.info("Market data imported succesfully.")
        
        date = datetime.strptime(start_date, '%Y-%m-%d')
        n_checks = int(rebalance_period / check_period)
        rebalanced_dates = []
 
        # initialize portfolios
        portfolio_list = []
        for i in range(n_quantiles):
            portfolio_list.append(portfolio(start_date, budget))
        logging.info(f"{len(portfolio_list)} portfolios created succesfully")

        while date < datetime.today():
            # rebalance portfolios
            quantile_list = self.create_quantiles(mk, n_quantiles, date.strftime('%Y-%m-%d'))
            logging.info(f"Stocks divided in {n_quantiles}")
            rebalanced_dates.append(date.strftime('%m/%y'))
            
            for i in range(n_quantiles):
                quantile_list[i] = quantile_list[i].reset_index(drop=True)
                portfolio_list[i].build(date.strftime('%Y-%m-%d'), quantile_list[i]['tickers'], quantile_list[i]['open'])
                logging.info(f"Bought stocks at {date} for portfolio nº {i}")

            # update performance
            for j in range(n_checks):
                date += timedelta(check_period)
                if date < datetime.today():
                    for i in range(n_quantiles):
                        portfolio_list[i].compute_performance(mk, date.strftime('%Y-%m-%d'))
                
                    logging.info(f"Updated performance for all portfolios at date {date}")

        logging.info(f"Finished backtesting. Returning portfolio performances...")
        
        # plot
        if self.less_is_better == True:
            ind = 'lowest' 
        else:
            ind = 'highest'
        
        fig = plt.figure(figsize=(16,32))
        ax = fig.add_subplot()
        for i in range(len(portfolio_list)):
            ax.plot([x[1] for x in portfolio_list[i].performance], label = f'{i+1}º quantil')
        plt.legend(loc='upper right')
        plt.ylabel('Returns (%)')
        plt.suptitle(f'Returns of {n_quantiles} portfolios by {ind} {self.factor}')
        plt.title(f'market = {market}, rebalance after {rebalance_period} days')
        plt.xlabel('date')
        plt.xticks([i for i in range(len(portfolio_list[i].performance)) if i%3 == 0], rebalanced_dates)
        ax.yaxis.tick_right()
        plt.show()
        
        return portfolio_list

class portfolio():

    def __init__(self, start_date, budget):

        self.positions = []
        self.initial_budget = budget
        self.value = budget
        self.performance = [(start_date, 100)] # lista de tuplas con fecha y valor
        self.last_rebalance = None

    def build(self, date, tickers, prices):
        ''' Dado un cuantil de acciones se construye un portfolio para el presupuesto actual.
        El presupuesto se divide por igual entre todas las acciones.'''

        self.positions.clear() # reiniciamos el portfolio
        
        n_stocks = len(tickers)
        
        money_per_stock = self.value / n_stocks

        for i in range(n_stocks):
            n_decimals = 10000 # 4 decimales, ignoramos error de truncamiento
            position = int(money_per_stock / prices[i] * n_decimals)
            self.positions.append((tickers[i], float(position)/n_decimals)) 

        self.last_rebalance = date # fecha del último rebalanceo

    def compute_performance(self, market_data, date):
        ''' De momento solo calcula el valor de un portfolio para una fecha X '''

        portfolio_value = 0
        tickers = [i for i, j in self.positions]
        shares = [j for i, j in self.positions]
        
        # Se espera una lista con los precios de cierre del día anterior. Si la acción ha sido deslistada debe devolver None
        mk = market_data.get(date, ['close'], tickers)
        prices = mk['close']

        for i in range(len(tickers)):
            # suma el valor actual de las posiciones
            portfolio_value += shares[i] * prices[i]
            '''if prices[i] is not None:
                portfolio_value += shares[i] * prices[i]
            else:
                portfolio_value += shares[i] * market_data.get_delisting_price[tickers[i]] # buscar el precio en fecha de delisting'''

            # suma los dividendos pagados
            # portfolio_value += market_data.get_paid_dividends(tickers[i], date - self.backtesting.check_period, date) # debe calcular los dividendos pagados por una lista de acciones entre dos fechas

        self.value = portfolio_value
        self.performance.append((date, int(self.value/self.initial_budget*100)))

def main():
    with strategy() as factor:
        factor.backtest()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(asctime)s: %(message)s')
    
    main()