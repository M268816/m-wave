# HOW TO USE:

## METHOD 1 - Convert Entire Worksheet:
 + Press ALT + F8 to open the Macro dialog
 + Select "ConvertTableToCSV"
 + Click "Run"
 + The macro will convert ALL data in the active worksheet to CSV format
 + Data is automatically copied to your clipboard
 + Paste into Notepad or directly into your local Excel

## METHOD 2 - Convert Selected Range Only:
 + Select the specific range of cells you want to convert
 + Press ALT + F8 to open the Macro dialog
 + Select "ConvertSelectionToCSV"
 + Click "Run"
 + Only the selected data will be converted to CSV format
 + Data is automatically copied to your clipboard
 + Paste into Notepad or directly into your local Excel


### OPTIONAL - CREATE A BUTTON:
To make it even easier, you can add a button to your Excel ribbon:

1. Right-click on the Excel ribbon and select "Customize the Ribbon"
2. Create a new tab or group
3. Under "Choose commands from", select "Macros"
4. Add "ConvertTableToCSV" and/or "ConvertSelectionToCSV" to your custom group
5. Click OK

Now you can run the macro with a single click!


## FEATURES:

 + Handles large datasets without truncation
 + Properly escapes commas, quotes, and line breaks in cell data
 + Preserves formula results (converts to displayed values)
 + Handles empty cells correctly
 + Shows progress for large datasets
 + Provides two options: entire worksheet or selected range only
 + Copies directly to clipboard for easy pasting
 + Works within Citrix restrictions (no file system access needed)


### CSV FORMAT DETAILS:

The macro creates proper CSV format:
 + Cells containing commas, quotes, or line breaks are wrapped in quotes
 + Quotes within cells are escaped (doubled)
 + Each row ends with a line break
 + Columns are separated by commas


### TROUBLESHOOTING:

If you get a clipboard error:
 + The macro will display the first 1000 characters in a message box
 + You can manually copy this text
 + For large datasets, you may need to process in smaller chunks using the selection method

If the macro doesn't appear:
 + Make sure macros are enabled in Excel
 + Check that you saved the file as .xlsm (macro-enabled workbook)

### WORKFLOW COMPARISON:

OLD WORKFLOW:
1. Manually select data in Citrix Excel Datalink
2. Copy to clipboard
3. Paste locally
    + Into local Notepad (to avoid truncation)
        - Copy loss less but messy data from notepad.
        - Paste into local Excel file.
        - Fix any formatting issues.
    + Into local Excel (lossy data)
        - Fix any lossy data
        - Fix any formatting issues.
4. Verify correct information.

NEW WORKFLOW:
1. Run macro in Citrix Excel (ALT + F8)
2. Paste into local Excel with text import wizard.
3. Verify the information is correct.


### TECHNICAL NOTES:

 + The macro uses MSForms.DataObject for clipboard access
 + No file system access required (works within Citrix restrictions)
 + Processes data row-by-row to handle large datasets efficiently
 + Memory-efficient for datasets with thousands of rows
