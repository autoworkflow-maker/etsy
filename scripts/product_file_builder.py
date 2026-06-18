import os
from openpyxl import Workbook
from openpyxl.styles import Font


class ProductFileBuilder:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def build_for_product(self, keyword, product_type):
        text = f"{keyword} {product_type}".lower()

        if (
            "budget" in text
            or "tracker" in text
            or "planner" in text
            or "template" in text
        ):

        return None

    def build_budget_tracker(self):
        filepath = os.path.join(self.folder, "tracker.xlsx")

        wb = Workbook()
        ws = wb.active
        ws.title = "Budget Tracker"

        headers = ["Date", "Description", "Category", "Income", "Expense", "Balance"]

        for col_num, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.font = Font(bold=True)

        wb.save(filepath)
        return filepath
