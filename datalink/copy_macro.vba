Sub ConvertTableToCSV()
    '===========================================================================
    ' Macro: ConvertTableToCSV
    ' Purpose: Convert all table data to CSV format and copy to clipboard
    ' This bypasses Excel's cell truncation issue when copying through Citrix
    '===========================================================================
    
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim lastCol As Long
    Dim i As Long, j As Long
    Dim csvText As String
    Dim cellValue As String
    Dim dataObj As Object
    
    ' Use the active worksheet
    Set ws = ActiveSheet
    
    ' Find the last row and column with data
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    
    ' Check if there's data
    If lastRow < 1 Or lastCol < 1 Then
        MsgBox "No data found in the worksheet!", vbExclamation
        Exit Sub
    End If
    
    ' Initialize progress
    Application.ScreenUpdating = False
    Application.StatusBar = "Converting to CSV format..."
    
    ' Build CSV string
    csvText = ""
    
    For i = 1 To lastRow
        For j = 1 To lastCol
            ' Get cell value
            cellValue = ws.Cells(i, j).Value
            
            ' Handle empty cells
            If IsEmpty(ws.Cells(i, j)) Then
                cellValue = ""
            End If
            
            ' Handle cells with formulas - get the displayed value
            If ws.Cells(i, j).HasFormula Then
                cellValue = ws.Cells(i, j).Text
            End If
            
            ' Escape quotes and wrap in quotes if contains comma, quote, or newline
            If InStr(cellValue, ",") > 0 Or InStr(cellValue, """") > 0 Or _
               InStr(cellValue, vbCr) > 0 Or InStr(cellValue, vbLf) > 0 Then
                cellValue = """" & Replace(cellValue, """", """""") & """"
            End If
            
            ' Add to CSV string
            csvText = csvText & cellValue
            
            ' Add comma separator (except for last column)
            If j < lastCol Then
                csvText = csvText & ","
            End If
        Next j
        
        ' Add line break (except for last row)
        If i < lastRow Then
            csvText = csvText & vbCrLf
        End If
        
        ' Update progress every 100 rows
        If i Mod 100 = 0 Then
            Application.StatusBar = "Converting to CSV format... Row " & i & " of " & lastRow
        End If
    Next i
    
    ' Copy to clipboard using DataObject
    On Error Resume Next
    Set dataObj = CreateObject("New:{1C3B4210-F441-11CE-B9EA-00AA006B1A69}")
    
    If dataObj Is Nothing Then
        ' Fallback method if MSForms DataObject is not available
        MsgBox "Unable to access clipboard. CSV data will be displayed in a message box.", vbInformation
        MsgBox Left(csvText, 1000) & vbCrLf & vbCrLf & "(Showing first 1000 characters only)", vbInformation
    Else
        dataObj.SetText csvText
        dataObj.PutInClipboard
        Set dataObj = Nothing
        
        MsgBox "Data successfully converted to CSV format and copied to clipboard!" & vbCrLf & vbCrLf & _
               "Rows: " & lastRow & vbCrLf & _
               "Columns: " & lastCol & vbCrLf & vbCrLf & _
               "You can now paste this into Notepad or directly into your local Excel.", vbInformation, "Success"
    End If
    
    ' Restore status bar
    Application.StatusBar = False
    Application.ScreenUpdating = True
    
End Sub


Sub ConvertSelectionToCSV()
    '===========================================================================
    ' Macro: ConvertSelectionToCSV
    ' Purpose: Convert only selected range to CSV format and copy to clipboard
    ' Useful when you only need a portion of the data
    '===========================================================================
    
    Dim rng As Range
    Dim i As Long, j As Long
    Dim csvText As String
    Dim cellValue As String
    Dim dataObj As Object
    
    ' Check if a range is selected
    If TypeName(Selection) <> "Range" Then
        MsgBox "Please select a range of cells first!", vbExclamation
        Exit Sub
    End If
    
    Set rng = Selection
    
    ' Initialize
    Application.ScreenUpdating = False
    Application.StatusBar = "Converting selection to CSV format..."
    
    ' Build CSV string
    csvText = ""
    
    For i = 1 To rng.Rows.Count
        For j = 1 To rng.Columns.Count
            ' Get cell value
            cellValue = rng.Cells(i, j).Value
            
            ' Handle empty cells
            If IsEmpty(rng.Cells(i, j)) Then
                cellValue = ""
            End If
            
            ' Handle cells with formulas
            If rng.Cells(i, j).HasFormula Then
                cellValue = rng.Cells(i, j).Text
            End If
            
            ' Escape quotes and wrap in quotes if contains comma, quote, or newline
            If InStr(cellValue, ",") > 0 Or InStr(cellValue, """") > 0 Or _
               InStr(cellValue, vbCr) > 0 Or InStr(cellValue, vbLf) > 0 Then
                cellValue = """" & Replace(cellValue, """", """""") & """"
            End If
            
            ' Add to CSV string
            csvText = csvText & cellValue
            
            ' Add comma separator (except for last column)
            If j < rng.Columns.Count Then
                csvText = csvText & ","
            End If
        Next j
        
        ' Add line break (except for last row)
        If i < rng.Rows.Count Then
            csvText = csvText & vbCrLf
        End If
    Next i
    
    ' Copy to clipboard
    On Error Resume Next
    Set dataObj = CreateObject("New:{1C3B4210-F441-11CE-B9EA-00AA006B1A69}")
    
    If dataObj Is Nothing Then
        MsgBox "Unable to access clipboard. CSV data will be displayed in a message box.", vbInformation
        MsgBox Left(csvText, 1000) & vbCrLf & vbCrLf & "(Showing first 1000 characters only)", vbInformation
    Else
        dataObj.SetText csvText
        dataObj.PutInClipboard
        Set dataObj = Nothing
        
        MsgBox "Selection successfully converted to CSV format and copied to clipboard!" & vbCrLf & vbCrLf & _
               "Rows: " & rng.Rows.Count & vbCrLf & _
               "Columns: " & rng.Columns.Count & vbCrLf & vbCrLf & _
               "You can now paste this into Notepad or directly into your local Excel.", vbInformation, "Success"
    End If
    
    ' Restore status bar
    Application.StatusBar = False
    Application.ScreenUpdating = True
    
End Sub
