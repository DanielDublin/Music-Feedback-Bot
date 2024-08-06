import json
import gspread
from google.oauth2.service_account import Credentials
from gspread import cell


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

    # adds updated rank info to spreadsheet for add_role
    def add_rank_spreadsheet(self, user_id, role):
        # find the row with the given user
        cell_row = self.sheet.find(str(user_id))
        if cell_row:
            user_row = cell_row.row
            # find the next available column in the user_row
            user_row_values = self.sheet.row_values(user_row)
            next_available_col = len(user_row_values) + 1
            self.sheet.update_cell(user_row, next_available_col, f"Ranked up to {role}")

    # adds updated rank info to spreadsheet for remove_role
    def remove_rank_spreadsheet(self, user_id, new_role):
        # find the row with the given user
        cell_row = self.sheet.find(str(user_id))
        if cell_row:
            user_row = cell_row.row
            # find the next available column in the user_row
            user_row_values = self.sheet.row_values(user_row)
            next_available_col = len(user_row_values) + 1
            self.sheet.update_cell(user_row, next_available_col, f"Ranked down to {new_role}")



# Example usage
key_file_path = '../Music-Feedback-Bot/mf-bot-402714-b394f37c96dc.json'
sheet_name = "MF BOT"
google_sheet = GoogleSheet(key_file_path, sheet_name)

