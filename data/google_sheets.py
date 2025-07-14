import gspread
from google.oauth2.service_account import Credentials
from config.settings import SHEET_ID, GOOGLE_CREDENTIAL

scopes = [
    'https://www.googleapis.com/auth/spreadsheets'
]

creds = Credentials.from_service_account_file(GOOGLE_CREDENTIAL, scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open_by_key(SHEET_ID)


