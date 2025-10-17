<#
PowerShell wrapper to run the Selenium-based yutura scraper.

Usage examples:
  # Activate conda environment and run pages 1..5 headless, save HTML
  .\run_scrape_yutura.ps1 -Start 1 -End 5 -Out "..\data\yutura_news_pages_1-5.csv" -SaveHtmlDir "..\data\yutura_pages_html" -Headless

Notes:
 - Run this script from the repository root: C:\Users\Owner\youtube
 - Ensure you have activated the intended conda environment (e.g., faceenv) before running, or pass full path to python.
#>

param(
    [int]$Start = 1,
    [int]$End = 1,
    [string]$Out = "data\yutura_news_pages_1-1.csv",
    [string]$SaveHtmlDir = $null,
    [switch]$Headless
)

Write-Host "Running yutura scraper: pages $Start..$End -> $Out"

# If you're using conda, ensure environment is active. We don't auto-activate here to avoid changing user's shell state.
# You can run: conda activate faceenv; .\scripts\run_scrape_yutura.ps1 ...

$python = "python"

$args = "scripts\scrape_yutura_pages_selenium.py --start $Start --end $End --out $Out"
if ($Headless) { $args += " --headless" }
if ($SaveHtmlDir) { $args += " --save-html-dir $SaveHtmlDir" }

Write-Host "Command: $python $args"

# Execute
& $python $args

if ($LASTEXITCODE -ne 0) {
    Write-Error "Scraper exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "Done. CSV: $Out"
