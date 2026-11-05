param([string]$DocName = 'Report NS3 DGHNM.docx')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $taskRoot $DocName
$renderRoot = Join-Path $PSScriptRoot 'part_i_render'
New-Item -ItemType Directory -Path $renderRoot -Force | Out-Null
$pdfPath = Join-Path $renderRoot 'part-i.pdf'
$wordApp = $null
$wordDoc = $null
try {
    $wordApp = New-Object -ComObject Word.Application
    $wordApp.Visible = $false
    $wordApp.DisplayAlerts = 0
    $wordDoc = $wordApp.Documents.Open($docPath, $false, $true)
    $wordDoc.Repaginate()
    $pageCount = $wordDoc.ComputeStatistics(2)
    $wordDoc.ExportAsFixedFormat($pdfPath, 17)
    Write-Output "Pages: $pageCount"
    Write-Output $pdfPath
}
finally {
    if ($null -ne $wordDoc) {
        $wordDoc.Close(0)
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordDoc)
    }
    if ($null -ne $wordApp) {
        $wordApp.Quit()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordApp)
    }
}
