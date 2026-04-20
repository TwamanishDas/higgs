# build_xlam.ps1
# Automatically creates higgs_excel.xlam from higgs_excel.bas
# Run from the office_addin\ folder:
#   powershell -ExecutionPolicy Bypass -File build_xlam.ps1

Write-Host ""
Write-Host "  Higgs Excel Add-in Builder" -ForegroundColor Cyan
Write-Host "  ──────────────────────────" -ForegroundColor DarkGray

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$basFile    = Join-Path $scriptDir "higgs_excel.bas"
$outFile    = Join-Path $scriptDir "higgs_excel.xlam"

if (-not (Test-Path $basFile)) {
    Write-Host "  ERROR: higgs_excel.bas not found in $scriptDir" -ForegroundColor Red
    exit 1
}

# ── Launch Excel via COM ──────────────────────────────────────────────────────
Write-Host "  Opening Excel..." -ForegroundColor Yellow
try {
    $xl = New-Object -ComObject Excel.Application
} catch {
    Write-Host "  ERROR: Could not start Excel. Is it installed?" -ForegroundColor Red
    exit 1
}

$xl.Visible        = $false
$xl.DisplayAlerts  = $false

try {
    # Create a new workbook
    $wb = $xl.Workbooks.Add()

    # Enable programmatic access to VBA project
    # (requires Trust Center > Macro Settings > "Trust access to the VBA project object model")
    $vbProj = $wb.VBProject

    # Remove the default empty module Sheet1 code if present
    # Import our .bas module
    Write-Host "  Importing VBA module..." -ForegroundColor Yellow
    $vbProj.VBComponents.Import($basFile) | Out-Null

    # Save as XLAM (add-in format = 55)
    Write-Host "  Saving as $outFile ..." -ForegroundColor Yellow
    $wb.SaveAs($outFile, 55)   # 55 = xlOpenXMLAddIn
    $wb.Close($false)

    Write-Host ""
    Write-Host "  SUCCESS: higgs_excel.xlam created!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open Excel"
    Write-Host "  2. File > Options > Add-ins"
    Write-Host "  3. At the bottom: Manage = 'Excel Add-ins'  > Go..."
    Write-Host "  4. Click Browse > select:  $outFile"
    Write-Host "  5. Tick 'Higgs Excel' > OK"
    Write-Host ""
    Write-Host "  Then add buttons to your Quick Access Toolbar (see README)." -ForegroundColor DarkGray

} catch {
    Write-Host ""
    Write-Host "  ERROR: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Most likely cause: VBA project access is blocked." -ForegroundColor Yellow
    Write-Host "  Fix: Excel > File > Options > Trust Center > Trust Center Settings"
    Write-Host "       > Macro Settings > tick 'Trust access to the VBA project object model'"
    Write-Host "  Then run this script again." -ForegroundColor DarkGray
} finally {
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
