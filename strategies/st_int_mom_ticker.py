#!/usr/local/bin/python3
#Strategy: Intraday Momentum EP Chan
import logging
#from kiteconnect import KiteConnect
from jugaad_trader import Zerodha
from jugaad_data.nse import stock_csv, stock_df
from kc_login import login
from order_book import order_book
import pandas as pd
import configparser
import math
import time
import datetime
import csv as xcl
#scheduler
from apscheduler.schedulers.background import BackgroundScheduler, BlockingScheduler

#sqlite3
import sqlite3

#Get config
config = configparser.ConfigParser()
config.read('config.ini')

API_KEY = config['KITE']['API_KEY']
API_SECRET = config['KITE']['API_SECRET']
CAPITAL = int(config['INT_MOM']['CAPITAL'])

log_format = '%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s'
log_date_format = '%Y-%m-%d:%H:%M:%S'
formatter = logging.Formatter(fmt=log_format, datefmt=log_date_format)
logging.basicConfig(format=log_format,
    datefmt=log_date_format,
    level=logging.INFO,
    filename='kiteconnect_app.log'
)

#Load SYMBOLS
csv=pd.read_csv('files/ind_nifty500list.csv')
SYMBOLS=csv['Symbol'].tolist()

class int_mom(object):
	def __init__(self, kite):
		self.kite = kite
		#strategy variables
		self.entryZscore=1
		self.lookback=20 # for MA
		#other variables
		self.op=None
		self.cl=None
		self.lo=None
		self.hi=None
		self.buy_price=None
		self.ma=None
		self.stdretC2C90d=None

		self.instruments = {}
		self.kws=None
		self.positions=None

		self.order_book=order_book.paper_order_book(kite=kite, strategy="int_mom")

	def load_data(self):
		logging.info("Loading data...")

		self.op = pd.read_csv('strategies/st_int_mom_data/op_live.csv',index_col=0)
		self.cl = pd.read_csv('strategies/st_int_mom_data/cl_live.csv',index_col=0)
		self.hi = pd.read_csv('strategies/st_int_mom_data/hi_live.csv',index_col=0)
		self.lo = pd.read_csv('strategies/st_int_mom_data/lo_live.csv',index_col=0)

		self.stdretC2C90d=self.cl.pct_change().rolling(90).std()
		self.buy_price=self.lo*(1-self.entryZscore*self.stdretC2C90d)
		self.ma=self.cl.rolling(self.lookback).mean()
		
		self.buy_price = self.buy_price.iloc[-1]
		self.ma = self.ma.iloc[-1]

		logging.info("Data loaded")

		return

	def _get_ohlcs(self, instruments):
		try:
			ret = self.kite.ohlc(instruments)
		except Exception as e:
			logging.error("Failed to fetch OHLC data")
			return None
		else:
			return ret

	def execute_strategy(self):
		logging.info("Scanning today's open prices for strategy...")
		#Get Quote for all 500 instruments
		instruments = ["NSE:"+SYMBOL for SYMBOL in SYMBOLS]
		ohlcs = self._get_ohlcs(instruments)
		#init
		candidates = []
		if ohlcs is not None:
			#In a loop, 
			for key in ohlcs:
				symbol = key.split(":")[1]
				ltp = ohlcs[key]['last_price']
				opp = ohlcs[key]['ohlc']['open']
				#OHLC returns 0, ignore symbol
				if opp == 0:
					continue
			#Calculate return gap from yesterday's low 	to today's opening
				ret_gap = (opp - self.lo.iloc[-1][symbol])/self.lo.iloc[-1][symbol]
				stdretC2C90d = self.stdretC2C90d.iloc[-1][symbol]
			#Check if the opening price < buy_price for the SYMBOL
			#Check if opening price > 20DSMA for the SYMBOL
			#place limit order near ltp
				if (opp < self.buy_price[symbol]):
					c = {
						"tradingsymbol":symbol,
						"instrument_token":ohlcs[key]['instrument_token'],
						"ret_gap":ret_gap,
						"stdretc2c90d":stdretC2C90d,
						"open":opp,
						"limit_order_price":ltp,
						"transaction_type":self.kite.TRANSACTION_TYPE_BUY
					}
					candidates.append(c)
		if len(candidates) == 0:
			logging.info("No candidates to trade today")
			print("No candidates to trade today")
			return 
		#Put them in a sorted list in ascending order of return gap
		candidates = sorted(candidates, key = lambda i: i['ret_gap'])[:10]

		cap_per_trade = math.floor(CAPITAL/len(candidates))
		
		for c in candidates:
			c['quantity']=math.floor(cap_per_trade/c['limit_order_price'])

		#Send the first 10 candidates to the order book to place limit orders
		logging.info("Setting candidates...")
		self.order_book.set_candidates(candidates)
		logging.info("Placing limit buy orders...")
		self.order_book.place_limit_order()
		
		return

	def close_positions(self):
		logging.info("Closing all positions for strategy...")
		
		open_positions = self.order_book.get_open_positions()
		
		if open_positions is None:
			return None

		candidates = []
		for pos in open_positions:
			c = {
				"tradingsymbol":pos.split(":")[1],
				"limit_order_price":open_positions[pos]['last_price'],
				"transaction_type":self.kite.TRANSACTION_TYPE_SELL,
				"quantity":open_positions[pos]['quantity']
			}
			candidates.append(c)

		logging.info("Setting candidates...")
		self.order_book.set_candidates(candidates)
		logging.info("Placing limit sell orders...")
		self.order_book.place_limit_order()

		return

	def export_report(self):
		conn = sqlite3.connect('order_book/paper_trade/int_mom_order_book.db')
		r=conn.execute("SELECT * FROM ORDER_BOOK;")
		
		with open("order_book/paper_trade/report.csv","a") as f:
			writer = xcl.writer(f)
			for row in r:
				ret = (row[7]-row[4])/row[4]
				writer.writerow([row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8], ret])
		
		conn.execute("DELETE FROM ORDER_BOOK;")
		conn.commit()
		conn.close()
		return

	def add_eod_data(self):

		instruments = ["NSE:"+SYMBOL for SYMBOL in SYMBOLS]
		ohlcs = self._get_ohlcs(instruments)

		dt = datetime.datetime.now() - datetime.timedelta(days=1)
		
		self.op=self.op.append(pd.Series(name=dt.strftime("%Y-%m-%d")))
		self.cl=self.cl.append(pd.Series(name=dt.strftime("%Y-%m-%d")))
		self.hi=self.hi.append(pd.Series(name=dt.strftime("%Y-%m-%d")))
		self.lo=self.lo.append(pd.Series(name=dt.strftime("%Y-%m-%d")))
		
		for key in ohlcs:
			symbol = key.split(":")[1]

			self.op.iloc[-1][symbol]=ohlcs[key]['ohlc']['open']
			self.cl.iloc[-1][symbol]=ohlcs[key]['ohlc']['close']
			self.hi.iloc[-1][symbol]=ohlcs[key]['ohlc']['high']
			self.lo.iloc[-1][symbol]=ohlcs[key]['ohlc']['low']

		self.op.drop(self.op.head(1).index, inplace=True)
		self.cl.drop(self.cl.head(1).index, inplace=True)
		self.hi.drop(self.hi.head(1).index, inplace=True)
		self.lo.drop(self.lo.head(1).index, inplace=True)

		self.op.to_csv('strategies/st_int_mom_data/op_live.csv')
		self.cl.to_csv('strategies/st_int_mom_data/cl_live.csv')
		self.hi.to_csv('strategies/st_int_mom_data/hi_live.csv')
		self.lo.to_csv('strategies/st_int_mom_data/lo_live.csv')

		return

	def add_eod_data_helper(self):
		from_date = datetime.date(2020,11,11)
		to_date = datetime.date(2021,5,11)

		df = stock_df(symbol="SBIN",from_date=from_date, to_date=to_date,series="EQ")

		df.set_index('DATE',inplace=True)
		df.sort_index(inplace=True)

		df.drop(["SERIES","PREV. CLOSE","LTP","OPEN","HIGH","LOW","CLOSE","VWAP","52W H","52W L","VOLUME","VALUE","NO OF TRADES","SYMBOL"],axis=1,inplace=True)

		op=df.copy()
		cl=df.copy()
		hi=df.copy()
		lo=df.copy()
		
		count=1

		stocks = pd.DataFrame(index=[0])

		for SYMBOL in SYMBOLS:
			print(str(count) + SYMBOL)
			# Download as pandas dataframe
			df = stock_df(symbol=SYMBOL, from_date=datetime.date(2020,11,11),
			            to_date=datetime.date(2021,5,11), series="EQ")
			df.set_index("DATE",inplace=True)
			
			op=op.join(df['OPEN'],rsuffix=count,how='outer')
			cl=cl.join(df['CLOSE'],rsuffix=count,how='outer')
			hi=hi.join(df['HIGH'],rsuffix=count,how='outer')
			lo=lo.join(df['LOW'],rsuffix=count,how='outer')

			if count==1:
				stocks['stock']=SYMBOL
			else:
				stocks['stock'+str(count)]=SYMBOL
			count+=1
			time.sleep(1)

		op.columns=stocks.values[0]
		cl.columns=stocks.values[0]
		hi.columns=stocks.values[0]
		lo.columns=stocks.values[0]

		op.to_csv('strategies/st_int_mom_data/op_live.csv')
		cl.to_csv('strategies/st_int_mom_data/cl_live.csv')
		hi.to_csv('strategies/st_int_mom_data/hi_live.csv')
		lo.to_csv('strategies/st_int_mom_data/lo_live.csv')

		return

	def on_ticks(self,ws,ticks):
		if self.positions is None:
			self.positions = self.order_book.get_open_positions()
		#TODO
		# Check if returns is more than 3%
		# If yes, close half of it and place SL order at cost + points to breakeven
		# Add SL order  function to order_book
		# If any changes to a position, remove from ticker subscription

		print("Ticks: {}".format(ticks))

	def on_connect(self,ws,response):
		
		orders = self.order_book.get_orders()
		tokens = []
		if orders is not None:
			for order in orders:
				tokens.append(order['instrument_token'])
				self.instruments[order['instrument_token']] = order['tradingsymbol']
		else:
			self.close_ticker()
		#tokens=[738561]
		ws.subscribe(tokens)
		ws.set_mode(ws.MODE_QUOTE, tokens)

	def on_close(self,ws,code,reason):
		ws.stop()

	def close_ticker(self):
		try:
			self.kws.close()
		except:
			pass
		return

	def start_ticker(self):
		self.kws = self.kite.ticker()
		# Assign the callbacks.
		self.kws.on_ticks = self.on_ticks
		self.kws.on_connect = self.on_connect
		self.kws.on_close = self.on_close
		
		self.kws.connect()

	def start(self):
		'''
		sched = BlockingScheduler()
		dt = datetime.datetime.today()
		sched.add_job(self.load_data, trigger="date",next_run_time=datetime.datetime(dt.year,dt.month,dt.day,8,59,0))
		sched.add_job(self.add_eod_data, trigger="date",next_run_time=datetime.datetime(dt.year,dt.month,dt.day,8,59,5))
		sched.add_job(self.load_data, trigger="date",next_run_time=datetime.datetime(dt.year,dt.month,dt.day,9,0,0))
		sched.add_job(self.execute_strategy, trigger="date",next_run_time=datetime.datetime(dt.year,dt.month,dt.day,9,15,5))
		#sched.add_job(self.start_ticker,trigger="date",next_run_time=datetime.datetime(dt.year,dt.month,dt.day,15,30,0))
		#sched.add_job(self.close_ticker,trigger="date",next_run_time=datetime.datetime(dt.year,dt.month,dt.day,15,28,0))
		sched.add_job(self.close_positions, trigger="date",next_run_time=datetime.datetime(dt.year,dt.month,dt.day,15,29,0))
		sched.add_job(self.export_report, trigger="date",next_run_time=datetime.datetime(dt.year,dt.month,dt.day,15,29,15))
		sched.start()
		'''
		self.start_ticker()
		
		return