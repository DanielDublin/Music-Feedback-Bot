import json
import gspread
import time
from datetime import timedelta
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
        
    async def get_outdated_for_all_users(self, guild):
        all_data = self.sheet.get_all_values()
        
        user_dates = []
        
        for row in all_data:
            if len(row) < 3:  # Skip rows that don't have enough data
                continue
                
            user_id = row[0]
            username = row[1]

            # check if user is still in the server
            try:
                member = guild.get_member(int(user_id))
                if member is None:
                    continue
            except:
                continue
            
            # Find the last date by going backwards through the row
            last_date_str = None
            last_role = None
            
            # Start from the end and work backwards, looking for date pattern
            for i in range(len(row) - 1, 1, -1):  # Start from end, go to index 2
                cell = row[i].strip() if row[i] else ""
                # Check if this looks like a date (contains slashes and numbers)
                if '/' in cell and any(c.isdigit() for c in cell):
                    last_date_str = cell
                    # The role should be in the cell before the date
                    if i > 0:
                        last_role = row[i - 1]
                    break
            
            # Skip if last role is MF Gilded, The Real MFrs, or Ranked down to Groupies
            if last_role and ("MF Gilded" in last_role or "The Real MFrs" in last_role or "Ranked down to Groupies" in last_role):
                continue
            
            if last_date_str and last_role:
                user_dates.append({
                    "user_id": user_id,
                    "username": username,
                    "last_role": last_role,
                    "last_date": last_date_str
                })
                        
        return user_dates
