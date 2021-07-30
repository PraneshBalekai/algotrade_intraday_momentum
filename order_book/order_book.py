#!/usr/local/bin/python3
#Strategy: Intraday Momentum EP Chan
import logging
import datetime
import pytz
import csv
from kiteconnect import KiteConnect
from kc_login import login
from order_book import order_book
import pandas as pd
import configparser

#sqlite3
import sqlite3

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

class order_book(object):
	def __init__(self, kite, strategy):
		self.kite = kite
		self.strategy = strategy
		self.candidates = [] #candidates identified by a strategy to enter positions in

	def set_candidates(self, candidates):
		self.candidates = candidates
		return

	def place_limit_order(self):
		for c in self.candidates:
			# Place an order
			try:
			    order_id = self.kite.place_order(
			        variety=self.kite.VARIETY_REGULAR,
			        exchange=self.kite.EXCHANGE_NSE,
			        tradingsymbol=c['tradingsymbol'],
			        transaction_type=c['transaction_type'],
			        quantity=c['quantity'],
			        product=self.kite.PRODUCT_CNC,
			        order_type=self.kite.ORDER_TYPE_LIMIT,
			        price=c['limit_order_price']
			    )

			    logging.info("{order_type} Order placed for {symbol} at {limit_order_price} ID is: {order_id}".format(order_type=c['transaction_type'], symbol=c['tradingsymbol'],order_id=order_id, limit_order_price=c['limit_order_price']))
			except Exception as e:
			    logging.error("{order_type} Order placement failed for {symbol}: {message}".format(order_type=c['transaction_type'], symbol=c['tradingsymbol'], message=e.message))

		return

	def get_open_positions(self):
		open_positions = self.kite.positions()
		return open_positions

	def get_orders(self):
		return self.kite.orders()

class paper_order_book(object):
	def __init__(self, kite, strategy):
		self.kite = kite
		self.strategy = strategy
		self.candidates = []

	def set_candidates(self, candidates):
		self.candidates = candidates
		return

	def place_limit_order(self):
		for c in self.candidates:
			# Place an order
			try:
				if c['transaction_type'] == self.kite.TRANSACTION_TYPE_BUY:
					conn = sqlite3.connect('order_book/paper_trade/'+self.strategy+'_order_book.db')
					conn.execute("INSERT INTO ORDER_BOOK (trading_symbol, ret_gap, stdretc2c90d, open_price, buy_price, quantity, buy_time) VALUES(\"{tradingsymbol}\",{ret_gap},{stdretc2c90d},{open_price},{buy_price},{quantity},\"{buy_time}\");".format(tradingsymbol=c['tradingsymbol'],ret_gap=c['ret_gap'],stdretc2c90d=c['stdretc2c90d'],open_price=c['open'],buy_price=c['limit_order_price'],quantity=c['quantity'],buy_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
					conn.commit()
					conn.close()
				elif c['transaction_type'] == self.kite.TRANSACTION_TYPE_SELL:
					conn = sqlite3.connect('order_book/paper_trade/'+self.strategy+'_order_book.db')
					conn.execute("UPDATE ORDER_BOOK SET sell_price={sell_price}, sell_time=\"{sell_time}\" WHERE trading_symbol=\"{tradingsymbol}\";".format(tradingsymbol=c['tradingsymbol'],sell_price=c['limit_order_price'],sell_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
					conn.commit()
					conn.close()

				logging.info("{order_type} Order placed for {symbol}. ID is: {order_id}".format(order_type=c['transaction_type'],symbol=c['tradingsymbol'],order_id="order_id"))
			except Exception as e:
			    logging.error("{order_type} Order placement failed for {symbol}: {message}".format(order_type=c['transaction_type'],symbol=c['tradingsymbol'], message=e))

		return

	def _get_ohlcs(self, instruments):
		try:
			ret = self.kite.ohlc(instruments)
		except Exception as e:
			logging.error("Failed to fetch OHLC data")
			return None
		else:
			return ret

	def _query_order_book(self):
		pos = {}
		conn = sqlite3.connect('order_book/paper_trade/'+self.strategy+'_order_book.db')
		r=conn.execute("SELECT * FROM ORDER_BOOK;")
		for row in r:
			pos["NSE:"+row[0]]={
				'quantity':row[4]
			}
		conn.close()
		return pos

	def get_open_positions(self):
		pos = self._query_order_book()
		instruments = [p for p,x in pos.items()]
		ohlcs = self._get_ohlcs(instruments)
		if ohlcs is None:
			return None
		for inst,value in ohlcs.items():
			pos[inst]['last_price']=ohlcs[inst]['last_price']
		return pos


		