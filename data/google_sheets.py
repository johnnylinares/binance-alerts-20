import gspread
from google.oauth2.service_account import Credentials

scopes = [
    'https://www.googleapis.com/auth/spreadsheets'
]

creds = Credentials.from_service_account_file('data/alert-20-binance-telegram-bot.json', scopes=scopes)
client = gspread.authorize(creds)

sheet_id = "1dwTKcXg0XnIIW-kqPBNHKaVoHjqJApHKsMEHvRmva3c"
sheet = client.open_by_key(sheet_id)


