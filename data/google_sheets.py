import gspread
from google.oauth2.service_account import Credentials
from config.settings import SHEET_ID

scopes = [
    'https://www.googleapis.com/auth/spreadsheets'
]

creds = Credentials.from_service_account_file('data/alert-20-binance-telegram-bot.json', scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open_by_key(SHEET_ID)


