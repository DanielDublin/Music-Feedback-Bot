import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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

    # time for sheet
    def time(self):
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        current_day = now.day
        return f"{current_month}/{current_day}/{current_year}"

    # adds user id + username if not in Google Sheet
    def add_user_spreadsheet(self, user_id, username):
        first_column = self.sheet.col_values(1)
        if str(user_id) not in first_column:
            self.sheet.append_row([str(user_id), username])

    # adds updated rank info to spreadsheet for add_role
    def update_rank_spreadsheet(self, user_id, role, is_rankup):
        # find the row with the given user
        cell_row = self.sheet.find(str(user_id))
        if cell_row:
            user_row = cell_row.row
            # find the next available column in the user_row
            user_row_values = self.sheet.row_values(user_row)
            next_available_col = len(user_row_values) + 1
            if is_rankup:
                self.sheet.update_cell(user_row, next_available_col, f"Ranked up to {role}")
            else:
                self.sheet.update_cell(user_row, next_available_col, f"Ranked down to {role}")
            # fill in date
            next_available_col = len(user_row_values) + 2
            self.sheet.update_cell(user_row, next_available_col, self.time())


    # gets the time of last role update
    def retrieve_time(self, user_id, role_name=None):
        # find the row with the given user
        cell_row = self.sheet.find(str(user_id))
        if cell_row:
            user_row = cell_row.row
            user_row_values = self.sheet.row_values(user_row)

            if role_name:
                # goes to last column of row and reads value (date)
                last_updated_date_col = len(user_row_values)
                last_updated_date = self.sheet.cell(user_row, last_updated_date_col).value
                return last_updated_date

            # if no role name provided, return the last column's value
            last_updated_date_col = len(user_row_values)
            if last_updated_date_col > 0:
                last_updated_date = self.sheet.cell(user_row, last_updated_date_col).value
                return last_updated_date

    # return the whole row of user data minus the first two columns (id and username)
    def get_history(self, user_id):
        # find the row with the given user
        cell_row = self.sheet.find(str(user_id))
        if cell_row:
            user_row = cell_row.row
            user_row_values = self.sheet.row_values(user_row)
            # exclude the first two columns
            user_row_values = user_row_values[2:]

            # group every two columns together
            paired_values = [user_row_values[i:i + 2] for i in range(0, len(user_row_values), 2)]

            # convert pairs to strings with bullet points
            paired_strings = [f"• {' '.join(pair)}" for pair in paired_values]

            return paired_strings

    def calculate_time(self, user_id):
        # get date previous role was added
        date_str = self.retrieve_time(user_id)
        if date_str:
            previous_date = datetime.strptime(date_str, "%m/%d/%Y")
            # get the current date
            current_date = datetime.now()
            # find difference
            time_difference = current_date - previous_date
            return time_difference.days

