#!/usr/local/bin/python3
import logging
from kiteconnect import KiteConnect
import configparser

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

def login():
	kite = KiteConnect(api_key=API_KEY)

	print("\n")
	print(kite.login_url())
	print("\n")

	request_token = input("Enter request_token after successful login: ")
	
	try:
		data = kite.generate_session(request_token, api_secret=API_SECRET)
		kite.set_access_token(data["access_token"])
	except Exception as e:
		logging.error("Error getting access token: ", e)
		return None

	return kite, access_token