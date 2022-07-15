#------------------------------------------------------------------------------
# Base de datos extraida a partir de la api de financial modeling
# Mejoras: hacer los requests de tres en tres, dividendos, deslistadas
#
#------------------------------------------------------------------------------
from numpy import empty
import requests 
import pandas as pd 
from datetime import datetime, timedelta
import json

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

    def create_dataframe(self,date_str,factor): 

        # Crea un df de tres columnas (ticker, apertura y factor) a partir de la base de datos (para una fecha dada)

        # Obten los tickers del mercado:
        tickers = self.symbols
        
        # Obten las cotizaciones a la apertura de esos tickers en esa fecha:
        # Si no se puede obtener la cotización, inseta un []
        tickers2 = []
        opens = []
        factors = []
        date = datetime.strptime(date_str, '%Y-%m-%d')
        for i in range(len(tickers)):
            first_date = self.dta[i]['historical'][-1]['date']
            if datetime.strptime(first_date, '%Y-%m-%d') < date:
                day = next((e for e in self.dta[i]['historical'] if datetime.strptime(e['date'], '%Y-%m-%d') <= date), None)                
                try:
                    factors.append(day[f'{factor}'])
                    tickers2.append(tickers[i])
                    opens.append(day['open'])
                except: pass
                
        '''while opens.count(None) == len(opens):
            for i in range(len(tickers)):

                try:
                    o = self.get_dta(date_str,tickers[i],'open')
                except:
                    o = None
                opens.append(o)
            date = datetime.strptime(date_str, '%Y-%m-%d')
            date -= timedelta(1)
            date_str = date.strftime('%Y-%m-%d')

        # Obten el factor para cada ticker en esa fecha
        # Si no se puede obtener el factor, inseta un []
        factors = []
        for i in range(len(tickers)):
            try:
               f = self.get_dta(date,tickers[i],f'{factor}')
            except:
                f = None
            factors.append(f)'''

        # Crea el df:
        return pd.DataFrame({'tickers': tickers2, 'opens': opens, 'factor':factors})#.dropna() #factor

    def get(self, date_str, data_points, tickers=[]):
        # si no le das tickers coge todos
        if not tickers:
            tickers = self.symbols
        
        # inicializa listas para cada variable pedida
        requested_data = [[]]
        n_points = len(data_points)
        for i in range(n_points):
            requested_data.append([])

        date = datetime.strptime(date_str, '%Y-%m-%d')

        for i in range(len(tickers)):
            
            day = None
            
            if len(tickers) == len(self.symbols):
                
                # si la fecha pedida es anterior a la primera de la empresa, ya sabemos que no sirve
                first_date = self.dta[i]['historical'][-1]['date'] 
                if datetime.strptime(first_date, '%Y-%m-%d') < date:

                    # cogemos la fecha más reciente que sea igual o anterior a la pedida. Sirve para delistings
                    day = next((e for e in self.dta[i]['historical'] if datetime.strptime(e['date'], '%Y-%m-%d') <= date), None)   
            
            else:

                historical = next((e['historical'] for e in self.dta if e['symbol'] == tickers[i]), None)
                day = next((e for e in historical if datetime.strptime(e['date'], '%Y-%m-%d') <= date), None)
            
            if day is not None:
                requested_data[0].append(tickers[i])
                
                # si alguno de los datos pedidos para la empresa está vacío, la elimina de la lista
                try:
                    for j in range(n_points):
                        requested_data[j+1].append(day[f'{data_points[j]}'])
                except: 
                    while j >= 0:
                        requested_data[j].pop()
                        j -= 1
        
        data_dict = {'tickers':requested_data[0]}
        for i in range (n_points):
            dict = {data_points[i]:requested_data[i+1]}
            data_dict.update(dict)

        return pd.DataFrame(data_dict)
    
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