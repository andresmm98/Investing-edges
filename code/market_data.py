#------------------------------------------------------------------------------
# Base de datos extraida a partir de la api de financial modeling
# Mejoras: hacer los requests de tres en tres, dividendos, deslistadas
#
#------------------------------------------------------------------------------
from numpy import empty
import requests 
import pandas as pd 

def req(request_url, api_key):
    base_url = f'https://financialmodelingprep.com/api/v3/'
    api_url = f'apikey={api_key}'
    url = f'{base_url}{request_url}{api_url}'
    response = requests.get(url).json()
    return response

class market_data():

    def __init__(self, market, n_stocks):
        
        # Inicializa una base de datos de tamaño n según el mercado, la información se guarda en dta y los tickers en symbols
        key_file = open('api_key.md','r')
        api_key = f'{key_file.readline()}'
        self.api_key = api_key
        
        request_url = f'quotes/{market}?'
        symbols = req(request_url,self.api_key)
        symbols = [t['symbol'] for t in symbols][0:n_stocks]

        dta = []
        empties = []
        for i in range(len(symbols)):
            request_url = f'historical-price-full/{symbols[i]}?'
            ans = req(request_url,self.api_key)
            if not ans:
                empties.append(symbols[i])
            else:
                dta.append(ans)#['historicalStockList'] si se hacen los request de tres en tres 

        for i in range(len(empties)):
            symbols.remove(empties[i])

        self.dta = dta 
        self.symbols = symbols

    def get_dta(self,date,symbol,var):
        
        # Consulta la base de datos para obtener un dato concreto de un ticker y en una fecha dada
        for i in range(len(self.dta)):
            try:
                if (self.dta[i]['symbol'] == symbol):
                    dta_index = next((index for (index, d) in enumerate(self.dta[i]['historical']) if d['date'] == date), None)
                    val = self.dta[i]['historical'][dta_index][var]
                    break
                else: val = None
            except: val = None
            
        return val

    def create_dataframe(self,date,factor): 

        # Crea un df de tres columnas (ticker, apertura y factor) a partir de la base de datos (para una fecha dada)

        # Obten los tickers del mercado:
        tickers = self.symbols
        
        # Obten las cotizaciones a la apertura de esos tickers en esa fecha:
        # Si no se puede obtener la cotización, inseta un []
        opens = []
        for i in range(len(tickers)):

            try:
                o = self.get_dta(date,tickers[i],'open')
            except:
                o = None
            opens.append(o)

        # Obten el factor para cada ticker en esa fecha
        # Si no se puede obtener el factor, inseta un []
        factors = []
        for i in range(len(tickers)):
            try:
               f = self.get_dta(date,tickers[i],f'{factor}')
            except:
                f = None
            factors.append(f)

        # Crea el df:
        return pd.DataFrame({'Tickers': tickers, 'Opens': opens, 'Factor':factors}).dropna() #factor

    def get_prices(self,tickers,date):

        # Devuelve una lista de los cierres 
        close = []
        for i in range(len(tickers)):
            try:
                c = self.get_dta(date,tickers[i],'close')
            except:
                c = None
            close.append(c)

        return pd.DataFrame({'Closes': close}).dropna() 

    def get_delisting_price(self,ticker):

       # Devuelve el último cierre de un ticker deslistado

       request_url = f'delisted-companies?page=0&'
       t = req(request_url,self.api_key)

       for i in range(len(t)):
        if(t[i]['symbol'] == ticker):
            d = t[i]['delistedDate']

        request_url = f'historical-price-full/{ticker}?from={d}&to={d}&'
        p = req(request_url,self.api_key)
        p = p['historical'][0]['close']

        return p 