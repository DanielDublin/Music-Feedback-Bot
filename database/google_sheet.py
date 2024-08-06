import json
import gspread
from google.oauth2.service_account import Credentials

class GoogleSheet:
    def __init__(self, key_file_path, sheet_name):
        self.key_file_path = key_file_path
        self.sheet_name = sheet_name
        self.gc = None
        self.sheet = None
        self.initialize_sheet()

    # connect to Google Sheet
    def initialize_sheet(self):
        with open(self.key_file_path, 'r') as key_file:
            key_file_dict = json.load(key_file)

            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            credentials = Credentials.from_service_account_info(key_file_dict, scopes=scope)
            self.gc = gspread.authorize(credentials)
            self.sheet = self.gc.open(self.sheet_name).sheet1
            print("Successfully connected to the Google Sheet")

    # adds user id + username if not in Google Sheet
    def add_user_spreadsheet(self, user_id, username):
        first_column = self.sheet.col_values(1)
        if str(user_id) not in first_column:
            self.sheet.append_row([str(user_id), username])



    # adds user id + username if not in Google Sheet
    def add_user_spreadsheet(self, user_id, username):
        first_column = self.sheet.col_values(1)
        if str(user_id) not in first_column:
            self.sheet.append_row([str(user_id), username])



# Example usage
key_file_path = '../Music-Feedback-Bot/mf-bot-402714-b394f37c96dc.json'
sheet_name = "MF BOT"
google_sheet = GoogleSheet(key_file_path, sheet_name)

