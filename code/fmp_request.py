#------------------------------------------------------------------------------
# HAZ UN REQUEST A LA API DE FINANCIAL MODELING 
#
# EJEMPLOS:
# request_url = stock/list? 
# request_url = delisted-companies?page=0&
# request_url = historical-price-full/AAPL?from=2018-03-12&to=2019-03-12&
# request_url = historical-price-full/AAPL?serietype=line&
# request_url = income-statement/AAPL?limit=120&
#
# 
#------------------------------------------------------------------------------
import requests 
import pandas as pd 

def request(request_url):
    api_key = f'59cb9e0309bfc1ef210167906090b097'
    base_url = f'https://financialmodelingprep.com/api/v3/'
    api_url = f'apikey={api_key}'
    url = f'{base_url}{request_url}{api_url}'
    response = requests.get(url)
    return pd.DataFrame(response.json())

data = request('historical-price-full/AAPL?from=2018-03-12&to=2019-03-12&')
print(data)
historical = pd.DataFrame(data['historical'][:])
print(historical)