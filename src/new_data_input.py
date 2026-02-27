import logging
import openpyxl
import pandas

logger = logging.getLogger(__name__)
FORMAT = "%(asctime)s:%(levelname)s:%(name)s::%(message)s"
logging.basicConfig(
    filename="error.log",
    filemode="w",
    format=FORMAT,
    encoding="utf-8",
    level=logging.DEBUG,
)


class NewData:
    """
    This class holds the processes for importing new data into the MTL/CMD.
    """

    def process(self) -> None:
        """
        Run the data transfer process.
        """
        sheet_names = {
            "MTL GxP": "MTL GxP",
            "CMD Enumeration": "CMD-Enumeration Sets",
            "CMD Categories": "CMD Categories",
            "CMD Tables": "CMD Tables",
            "CMD Event Frames": "CMD-Event Frame Templates",
            "CMD Elements": "CMD-Element Tempaltes",
        }
        table_names = {
            "MTL-Analytics-VAL&PROD": "Table5",
            "MTL GxP-VAL": "Table2",
            "MTL GxP-PROD": "Table3",
            "CMD-Enumeration Sets-VAL": "Table6",
            "CMD-Enumeration Sets-PROD": "Table7",
            "CMD Categories-VAL": "Table8",
            "CMD Categories-PROD": "Table9",
            "CMD Tables-VAL": "Table10",
            "CMD Tables-PROD": "Table1012",
            "CMD-Event Frame Templates-VAL": "Table14",
            "CMD-Event Frame Templates-PROD": "Table1416",
            "CMD-Element Templates-VAL": "Table12",
            "CMD-Element Templates-PROD": "Table13",
        }
        if self.selected_data_type.get() == "MTL Analytics":
            sheet = "MTL-Analytics-VAL&PROD"
            return print(f"Selected: {sheet}, {table_names[sheet]}")
        else:
            sheet = sheet_names[self.selected_data_type.get()]
        if self.selected_data_env.get() == "prod" and sheet:
            sheet = sheet + "-PROD"
        else:
            sheet = sheet + "-VAL"
        if sheet:
            print(f"Sheet Selected: {sheet}")
            print(f"Table Selected: {table_names[sheet]}")
        else:
            print(f"ERROR SELECTING OPTIONS!")

        def subroutine():
            """
            Pushes the process of loading the information to input to another
            thread.
            """
            try:
                # load the mtl workbook
                mtl_workbook = load_workbook(self.mtl_file_path.get(), data_only=True)
                # find the appropriate table for the selected file options
                mtl_sheetname = sheet
                mtl_worksheet = mtl_workbook[mtl_sheetname]
                mtl_table_name = table_names[mtl_sheetname]
                mtl_table_range = mtl_worksheet.tables[mtl_table_name].ref
                mtl_table_data = mtl_worksheet[mtl_table_range]
                # convert the worksheet's table data string into a table
                mtl_conversion = [
                    [cell.value for cell in row] for row in mtl_table_data
                ]
                # return the header columns
                mtl_headers = mtl_conversion[0]
                mtl_rows = mtl_conversion[1:]  # Not needed for inputting data
                # convert the tabled data into a pd dataframe
                mtl_df = pd.DataFrame(mtl_rows, columns=mtl_headers)
                print("MTL Table Debug:")
                print(mtl_df)
                mtl_workbook.close()
                # testing the table by outputting the dataframe to the preview table
                input_workbook = load_workbook(
                    self.input_data_file_path.get(), data_only=True
                )
                input_worksheet = input_workbook.active
                input_conversion = list(input_worksheet.values)
                input_header = input_conversion[0]
                input_rows = input_conversion[1:]
                input_table = pd.DataFrame(input_rows, columns=input_header)
                input_workbook.close()
                print("Input data debug:")
                print(input_table)
                temp_table = input_table.copy()
                temp_table = temp_table[
                    ["Name", "Description", "datasecurity", "pointtype"]
                ]
                # adding the first few rows of data to the preview table
                for i in range(len(temp_table)):
                    self.insert_row(
                        i,
                        temp_table.iloc[i, 0],
                        temp_table.iloc[i, 1],
                        temp_table.iloc[i, 2],
                        temp_table.iloc[i, 3],
                    )
            except Exception as e:
                print(f"Could not load worksheet data.")
                print(e)
            self.window.after_idle(self.progress_bar.stop)

        self.progress_bar.start(15)
        thread = threading.Thread(target=subroutine, daemon=True)
        thread.start()

    def test(self):
        logger.info("This is info.")
        logger.debug("This is debug.")
        logger.warning("This is warning.")
        logger.error("This is error.")
        logger.critical("This is critical.")


if __name__ == "__main__":
    app = NewData()
    app.test()
