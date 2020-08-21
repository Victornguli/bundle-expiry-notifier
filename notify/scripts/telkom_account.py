import logging
import os
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv, find_dotenv

# Load env since this is run outside wsgi environment
load_dotenv(find_dotenv())

MAX_RETRIES = 3
log_path = os.getenv("LOG_PATH")
logging.basicConfig(level = logging.INFO, filename = os.path.join(log_path, "logs.log"))

display = Display(visible = 0, size = (800, 600))
display.start()


class TelkomAccountManager:
	"""Telkom mobile account manager class"""

	def __init__(self):
		self.phone_number = os.getenv('PHONE_NUMBER')
		self.password = os.getenv('PASSWORD')
		self.login_url = os.getenv('TELKOM_LOGIN_URL')

		options = webdriver.ChromeOptions()
		options.add_argument('--no-sandbox')
		self.driver = webdriver.Chrome(os.getenv('CHROMEDRIVER_PATH'), options = options)

	def login(self):
		self.driver.get(self.login_url)
		form = WebDriverWait(self.driver, 10).until(
			EC.presence_of_element_located((By.ID, 'userLoginForm'))
		)
		phone_input = self.driver.find_element_by_id('number')
		password_input = self.driver.find_element_by_id('pwd')
		phone_input.send_keys(self.phone_number)
		password_input.send_keys(self.password)
		form.submit()

	def get_balances(self):
		airtime_bal = self.driver.find_element_by_id('txtCurrBal').get_property('value')
		data_balance = self.driver.find_element_by_xpath(
			'//*[@id="tableAcctContent"]/tbody/tr[5]/td[2]/input').get_property('value')
		return {'airtime': airtime_bal, 'data': data_balance}

	@staticmethod
	def parse_balances(balance_data):
		"""
		Parses the text balance information into integers
		:param balance_data: The scraped textual information about the current balance
		:type balance_data: dict
		:return: Parsed balance information
		:rtype: dict
		"""
		airtime, data = balance_data.get('airtime').lower(), balance_data.get('data').lower()
		data = int(float(data.replace('mb', '')))
		airtime = int(float((airtime.replace('ksh', ''))))
		return {'data': data, 'airtime': airtime}

	@staticmethod
	def check_balances(parsed_data):
		"""
		Checks the data and airtime balance and performs necessary actions
		"""
		data, airtime = parsed_data.get('data'), parsed_data.get('airtime')
		balance_info = f'Current data balance is: {data}MB and current airtime balance is KES{airtime}.'
		if data >= 1500:
			# send notification directing user to buy 700MB
			instructions = 'You should manually initiate 700MB bundle purchase of KES60.'
		elif data < 1500 and airtime >= 100:
			# Proceed to automatically reload 2GB bundle
			instructions = 'You should manually initiate 2GB bundle purchase of KES100.'
		else:
			# Notification with instructions to buy airtime
			instructions = 'Low airtime balance. Recharge your account and initiate bundle purchase.'
		return f'{instructions}\n{balance_info}'

	def run(self):
		try:
			self.login()
			WebDriverWait(self.driver, 10).until(
				EC.presence_of_element_located((By.ID, 'txtCurrBal'))
			)
			balance = self.parse_balances(self.get_balances())
			return balance
		except Exception as ex:
			logging.exception(f'An error occurred while opening telkom account: {str(ex)}')
			# account.driver.quit()
			raise ex
