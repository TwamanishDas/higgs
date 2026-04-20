Attribute VB_Name = "HiggsExcel"
Option Explicit

' ============================================================
'  Higgs Excel VBA Add-in
'  Sends selected range / sheet summary to the Higgs desktop
'  widget running on localhost:5050.
'
'  Install: File > Options > Add-ins > Manage: Excel Add-ins
'           > Browse > select higgs_excel.xlam
' ============================================================

Private Const HIGGS_URL As String = "http://127.0.0.1:5050"


' ── JSON helpers ─────────────────────────────────────────────────────────────

Private Function JsonEsc(s As String) As String
    s = Replace(s, "\", "\\")
    s = Replace(s, """", "\""")
    s = Replace(s, Chr(10), "\n")
    s = Replace(s, Chr(13), "\r")
    s = Replace(s, Chr(9), "\t")
    JsonEsc = s
End Function

Private Function ValToJson(v As Variant) As String
    If IsEmpty(v) Or IsNull(v) Then
        ValToJson = "null"
    ElseIf VarType(v) = vbBoolean Then
        ValToJson = IIf(v, "true", "false")
    ElseIf IsNumeric(v) Then
        ValToJson = CStr(v)
    Else
        ValToJson = """" & JsonEsc(CStr(v)) & """"
    End If
End Function

Private Function ArrayToJson(arr As Variant, maxRows As Long, maxCols As Long) As String
    Dim r As Long, c As Long
    Dim rb As Long, cb As Long
    Dim rows As Long, cols As Long
    Dim rowBuf() As String, colBuf() As String

    rb = LBound(arr, 1): cb = LBound(arr, 2)
    rows = Application.Min(UBound(arr, 1) - rb + 1, maxRows)
    cols = Application.Min(UBound(arr, 2) - cb + 1, maxCols)

    ReDim rowBuf(0 To rows - 1)
    For r = 0 To rows - 1
        ReDim colBuf(0 To cols - 1)
        For c = 0 To cols - 1
            colBuf(c) = ValToJson(arr(rb + r, cb + c))
        Next c
        rowBuf(r) = "[" & Join(colBuf, ",") & "]"
    Next r
    ArrayToJson = "[" & Join(rowBuf, ",") & "]"
End Function


' ── HTTP helper ───────────────────────────────────────────────────────────────

Private Function PostJson(endpoint As String, body As String) As Boolean
    On Error GoTo Fail
    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP.6.0")
    http.Open "POST", HIGGS_URL & endpoint, False
    http.setRequestHeader "Content-Type", "application/json"
    http.Send body
    PostJson = (http.Status = 200)
    Set http = Nothing
    Exit Function
Fail:
    PostJson = False
    Set http = Nothing
End Function


' ── Public macros ─────────────────────────────────────────────────────────────

' Sends the currently selected cell range to Higgs.
' Assign to a Quick Access Toolbar button or keyboard shortcut.
Public Sub SendSelectionToHiggs()
    On Error GoTo ErrHandler

    Dim rng As Range
    Set rng = Selection
    If rng Is Nothing Or rng.Cells.Count = 0 Then
        MsgBox "Select a range first.", vbInformation, "Higgs": Exit Sub
    End If

    Dim maxR As Long: maxR = Application.Min(rng.Rows.Count, 30)
    Dim maxC As Long: maxC = Application.Min(rng.Columns.Count, 20)
    Dim lr As Range: Set lr = rng.Resize(maxR, maxC)

    ' Get values and formulas
    Dim vals As Variant, fmls As Variant
    If maxR = 1 And maxC = 1 Then
        ReDim vals(1 To 1, 1 To 1): vals(1, 1) = lr.Value
        ReDim fmls(1 To 1, 1 To 1): fmls(1, 1) = lr.Formula
    Else
        vals = lr.Value
        fmls = lr.Formula
    End If

    ' Detect header row: first row all non-empty strings
    Dim hasHeader As String: hasHeader = "false"
    If maxR > 1 Then
        Dim allStr As Boolean: allStr = True
        Dim c As Long
        For c = LBound(vals, 2) To LBound(vals, 2) + maxC - 1
            If Not (VarType(vals(LBound(vals, 1), c)) = vbString _
                    And Len(Trim(CStr(vals(LBound(vals, 1), c)))) > 0) Then
                allStr = False: Exit For
            End If
        Next c
        If allStr Then hasHeader = "true"
    End If

    Dim json As String
    json = "{"
    json = json & """sheet"":"   & """" & JsonEsc(ActiveSheet.Name)                   & ""","
    json = json & """address"":"  & """" & JsonEsc(rng.Address(External:=True))       & ""","
    json = json & """row_count"":" & rng.Rows.Count                                   & ","
    json = json & """col_count"":" & rng.Columns.Count                                & ","
    json = json & """has_header"":" & hasHeader                                        & ","
    json = json & """values"":"   & ArrayToJson(vals, maxR, maxC)                     & ","
    json = json & """formulas"":" & ArrayToJson(fmls, maxR, maxC)                     & ","
    json = json & """source"":""selection"""
    json = json & "}"

    If PostJson("/api/excel/selection", json) Then
        Application.StatusBar = "Higgs: selection sent  ✓"
        Application.OnTime Now + TimeValue("00:00:03"), "'" & ThisWorkbook.Name & "'!ClearStatus"
    Else
        MsgBox "Higgs is not running." & vbCr & vbCr & _
               "Start the desktop widget first:  python main.py", _
               vbExclamation, "Higgs"
    End If
    Exit Sub
ErrHandler:
    MsgBox "Error " & Err.Number & ": " & Err.Description, vbCritical, "Higgs"
End Sub


' Sends the active sheet headers + a 5-row sample to Higgs.
Public Sub SendSheetSummaryToHiggs()
    On Error GoTo ErrHandler

    Dim ws As Worksheet: Set ws = ActiveSheet
    Dim ur As Range
    On Error Resume Next
    Set ur = ws.UsedRange
    On Error GoTo ErrHandler

    If ur Is Nothing Then
        MsgBox "The active sheet is empty.", vbInformation, "Higgs": Exit Sub
    End If

    Dim allV As Variant
    If ur.Cells.Count = 1 Then
        ReDim allV(1 To 1, 1 To 1): allV(1, 1) = ur.Value
    Else
        allV = ur.Value
    End If

    Dim totalR As Long: totalR = UBound(allV, 1) - LBound(allV, 1) + 1
    Dim totalC As Long: totalC = UBound(allV, 2) - LBound(allV, 2) + 1

    ' Build headers JSON array
    Dim i As Long
    Dim hdr() As String: ReDim hdr(0 To totalC - 1)
    For i = 0 To totalC - 1
        hdr(i) = """" & JsonEsc(CStr(allV(LBound(allV, 1), LBound(allV, 2) + i))) & """"
    Next i

    ' col_counts: non-empty cells per column
    Dim colCnt() As String: ReDim colCnt(0 To totalC - 1)
    Dim r As Long, cnt As Long
    For i = 0 To totalC - 1
        cnt = 0
        For r = LBound(allV, 1) To UBound(allV, 1)
            If Not IsEmpty(allV(r, LBound(allV, 2) + i)) _
               And allV(r, LBound(allV, 2) + i) <> "" Then cnt = cnt + 1
        Next r
        colCnt(i) = CStr(cnt)
    Next i

    Dim sR As Long: sR = Application.Min(5, totalR)
    Dim sC As Long: sC = Application.Min(20, totalC)

    Dim json As String
    json = "{"
    json = json & """sheet"":"      & """" & JsonEsc(ws.Name)                          & ""","
    json = json & """address"":"    & """" & JsonEsc(ur.Address(External:=True))       & ""","
    json = json & """row_count"":"  & totalR                                            & ","
    json = json & """col_count"":"  & totalC                                            & ","
    json = json & """headers"":"    & "[" & Join(hdr, ",") & "]"                       & ","
    json = json & """sample"":"     & ArrayToJson(allV, sR, sC)                        & ","
    json = json & """col_counts"":"  & "[" & Join(colCnt, ",") & "]"                   & ","
    json = json & """source"":""sheet_summary"""
    json = json & "}"

    If PostJson("/api/excel/selection", json) Then
        Application.StatusBar = "Higgs: sheet summary sent  ✓"
        Application.OnTime Now + TimeValue("00:00:03"), "'" & ThisWorkbook.Name & "'!ClearStatus"
    Else
        MsgBox "Higgs is not running." & vbCr & vbCr & _
               "Start the desktop widget first:  python main.py", _
               vbExclamation, "Higgs"
    End If
    Exit Sub
ErrHandler:
    MsgBox "Error " & Err.Number & ": " & Err.Description, vbCritical, "Higgs"
End Sub


' Check if the Higgs widget is reachable
Public Sub CheckHiggsConnection()
    On Error GoTo NotRunning
    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP.6.0")
    http.Open "GET", HIGGS_URL & "/api/ping", False
    http.Send
    If http.Status = 200 Then
        MsgBox "Higgs is running and connected!", vbInformation, "Higgs"
    Else
        GoTo NotRunning
    End If
    Set http = Nothing
    Exit Sub
NotRunning:
    Set http = Nothing
    MsgBox "Higgs is not running." & vbCr & vbCr & _
           "Start the widget:  python main.py", vbExclamation, "Higgs"
End Sub


' Clears the Excel status bar (called after 3 s delay)
Public Sub ClearStatus()
    Application.StatusBar = False
End Sub
