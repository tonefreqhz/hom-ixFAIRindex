# ============================================================
#  HOME@IX FAIR-INDEX W-ANCHOR VERIFY
#  Part of the tonefreqhz W-Anchor Protocol trilogy:
#    hom-ixFAIRindex | reproducible-self-pub-kit | DoughForge
#
#  Run this at the start of every session.
#  Paste full output into your AI chat before any instruction.
#  An AI that has not seen this output is not anchored.
# ============================================================

Write-Host ""
Write-Host "============================================================"
Write-Host " HOME@IX FAIR-INDEX W-ANCHOR VERIFY"
Write-Host "============================================================"
Write-Host ""

$root = "C:\Users\peewe\OneDrive\Desktop\homeix"
$ok   = $true

function Check-Path($label, $path) {
    $padLabel = $label.PadRight(32)
    if (Test-Path -LiteralPath $path) {
        Write-Host "  [OK     ] $padLabel $path"
    } else {
        Write-Host "  [MISSING] $padLabel $path"
        $script:ok = $false
    }
}

Write-Host "=== W-Anchor - Path Verification ==="
Write-Host ""
Write-Host "  -- Anchor & Protocol --"
Write-Host ""
Check-Path "Repo Root"                   $root
Check-Path "ANCHOR.md"                   "$root\ANCHOR.md"
Check-Path "anchor.py"                   "$root\anchor.py"
Check-Path "anchor_verify.ps1"           "$root\anchor_verify.ps1"

Write-Host ""
Write-Host "  -- Source & Pipeline --"
Write-Host ""
Check-Path "src/paths.py"                "$root\src\paths.py"
Check-Path "src/__init__.py"             "$root\src\__init__.py"
Check-Path "Orchestrator"                "$root\sweep_up\inbox\assemble_full_ebook.py"
Check-Path "rebuild_publish.ps1"         "$root\sweep_up\inbox\rebuild_publish.ps1"

Write-Host ""
Write-Host "  -- Canonical Inputs --"
Write-Host ""
Check-Path "inputs/canonical/"           "$root\inputs\canonical"
Check-Path "homeatix_model.csv"          "$root\inputs\canonical\homeatix_model.csv"
Check-Path "dwellings_stock.csv"         "$root\inputs\canonical\dwellings_stock_by_tenure_uk_annual.csv"
Check-Path "CHECKSUMS.sha256"            "$root\inputs\provenance\CHECKSUMS.sha256"

Write-Host ""
Write-Host "  -- Outputs (missing before first build is normal) --"
Write-Host ""
Check-Path "outputs/"                    "$root\outputs"
Check-Path "outputs/figures/"           "$root\outputs\figures"
Check-Path "fig_fair_level.png"          "$root\outputs\figures\fig_fair_level.png"
Check-Path "fig_fair_contrib.png"        "$root\outputs\figures\fig_fair_contrib.png"
Check-Path "features_quarterly.csv"      "$root\outputs\features_quarterly.csv"
Check-Path "features_quarterly_fair.csv" "$root\outputs\features_quarterly_with_fair.csv"
Check-Path "fair_assets/"               "$root\outputs\fair_assets"

Write-Host ""
Write-Host "  -- Publication Bundle --"
Write-Host ""
Check-Path "publication/"               "$root\publication"
Check-Path "print_latest/"              "$root\publication\print_latest"
Check-Path "print_latest/index.html"    "$root\publication\print_latest\index.html"

Write-Host ""
Write-Host "  -- Assets --"
Write-Host ""
Check-Path "assets/cover/"              "$root\assets\cover"
Check-Path "base_cover.png"             "$root\assets\cover\base_cover.png"
Check-Path "front_cover.jpg"            "$root\assets\cover\front_cover.jpg"
Check-Path "branding/Final-Logo"        "$root\assets\branding\Final-Logo-white.png"

Write-Host ""
if ($ok) {
    Write-Host "  OK All paths verified. Session is anchored."
} else {
    Write-Host "  WARNING: MISSING paths above — fix before proceeding."
    Write-Host "  An AI that has not seen this output is not anchored and will drift."
}

Write-Host ""
Write-Host "============================================================"
Write-Host ""

# Git state
Write-Host "=== Git State ==="
Write-Host ""
Set-Location $root
git branch --show-current
git status --short
Write-Host ""
git log --oneline -5
Write-Host ""
Write-Host "============================================================"
Write-Host ""
