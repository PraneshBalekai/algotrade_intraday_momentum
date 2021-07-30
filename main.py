#!/usr/local/bin/python3
#Strategy: Intraday Momentum EP Chan
import logging
#from kiteconnect import KiteConnect
from jugaad_trader import Zerodha
from kc_login import login
import pandas as pd
import configparser
from strategies import st_int_mom_v2
from strategies import st_int_mom

#Get config
config = configparser.ConfigParser()
config.read('config.ini')

API_KEY = config['KITE']['API_KEY']
API_SECRET = config['KITE']['API_SECRET']

log_format = '%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s'
log_date_format = '%Y-%m-%d:%H:%M:%S'
formatter = logging.Formatter(fmt=log_format, datefmt=log_date_format)
logging.basicConfig(format=log_format,
    datefmt=log_date_format,
    level=logging.INFO,
    filename='kiteconnect_app.log'
)

def main(kite):
	#starts strategy in a continuous loop. Need to thread this if implementing multiple strategies
	st = st_int_mom.int_mom(kite).start()

if __name__ == '__main__':
	#kite, access_token = login()
	kite = Zerodha()
	#kite.enc_token = "uP8dxtUQPO5dOh7HbEFdKcpeGrt9eJOLBp/4+qQra3ZOi0gKVPc7CMSMe1/H1H/HIQd/C5nElYWfnDhQ9j5sTTiC8ho95Q=="
 
	# Set access token loads the stored session.
	# Name chosen to keep it compatible with kiteconnect.
	kite.set_access_token()

	if kite != None:
		main(kite)
	else:
		logging.error("Login Failed.")