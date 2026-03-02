param(
  [string]$ProjectRoot = "C:\Users\peewe\OneDrive\Desktop\homeix"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------- 0) Make console + Python UTF-8 (prevents Δ / UnicodeEncodeError) ----------
# Note: chcp output is suppressed; this mainly helps older host configs.
try { chcp 65001 | Out-Null } catch {}
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new() } catch {}

Set-Location $ProjectRoot

# --- Use venv Python (no global 'py' launcher required) ---
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  throw "Venv python not found at: $Python"
}

# Silence Pillow DeprecationWarning noise (keeps real errors visible)
$env:PYTHONWARNINGS = "ignore::DeprecationWarning"


$stamp = Get-Date -Format "yyyyMMdd_HHmmss"

# ---------- 1) Archive existing outputs ----------
if (Test-Path ".\outputs") {
  $archive = ".\outputs_archive_$stamp"
  Write-Host "Archiving outputs -> $archive"
  Copy-Item ".\outputs" $archive -Recurse -Force
} else {
  New-Item -ItemType Directory -Path ".\outputs" | Out-Null
}

# ---------- 2) Clean outputs (tier 1+) ----------
Write-Host "Cleaning .\outputs\*"
Remove-Item ".\outputs\*" -Recurse -Force -ErrorAction SilentlyContinue

# ---------- 3) Rebuild in safe order ----------
$steps = @(
  "sweep_up\inbox\build_forward_indicator.py",
  "sweep_up\inbox\choose_calm_baseline.py",
  "sweep_up\inbox\compute_fair.py",
  "sweep_up\inbox\plot_fair.py",
  "sweep_up\inbox\build_fair_outputs.py",
  "sweep_up\inbox\make_domain_terms.py",
  "sweep_up\inbox\fix_domain_terms.py",
  "sweep_up\inbox\backtest_ew_crash_warning.py"
)

foreach ($s in $steps) {
  if (!(Test-Path ".\$s")) { throw "Missing script: $s" }

  Write-Host "`nRunning: $s"
  & $Python ".\$s"

  if ($LASTEXITCODE -ne 0) {
    throw "Step failed (exit code $LASTEXITCODE): $s"
  }
}

# ---------- 4) Create publication print folder ----------
$pub = ".\publication\print_$stamp"
New-Item -ItemType Directory -Force -Path $pub | Out-Null

# Curate what goes into the print bundle (adjust freely)
$include = @(
  ".\outputs\fair_summary_baseline_stats.csv",
  ".\outputs\fair_assets\fair_quarterly_audit.csv",
  ".\outputs\fair_assets\fig_fair_contributions.png",
  ".\outputs\fair_assets\fig_fair_level.png",
  ".\outputs\fair_assets\anim_fair_direction_of_flow.gif",
  ".\outputs\draft_paper_assets\ew_crash_starts.csv",
  ".\outputs\draft_paper_assets\ew_events_lead_times.csv",
  ".\outputs\draft_paper_assets\ew_summary.json",
  ".\outputs\draft_paper_assets\fig_avg_leadtime_by_signal.png",
  ".\outputs\draft_paper_assets\fig_price_and_fair_with_crash_starts.png",
  ".\outputs\draft_paper_assets\domain_terms_state1_state2.csv",
  ".\outputs\figures\fig_domain_turnover_pct_q.png",
  ".\outputs\figures\fig_domain_mortgage_stock_gbp_bn.png",
  ".\outputs\features_quarterly_with_fair.csv",
  ".\outputs\features_quarterly.csv"
)

foreach ($p in $include) {
  if (Test-Path $p) {
    Copy-Item $p $pub -Force
  } else {
    Write-Host "WARN: not found (skipping) $p"
  }
}

# Optional: also copy the HTML drafts into the print folder (useful as source refs)
if (Test-Path ".\homeix_fair_paper.html")     { Copy-Item ".\homeix_fair_paper.html" $pub -Force }
if (Test-Path ".\homeix_followup_paper.html") { Copy-Item ".\homeix_followup_paper.html" $pub -Force }

# ---------- 5) Assemble FULL combined ebook HTML into the print folder ----------
$ebookScriptCandidates = @(
  ".\assemble_full_ebook.py",
  ".\sweep_up\inbox\assemble_full_ebook.py"
)

$ebookScript = $ebookScriptCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($null -ne $ebookScript) {
  Write-Host "`nAssembling combined full ebook -> $pub\index.html"
  & $Python (Join-Path $ProjectRoot $ebookScript.TrimStart(".\")) --outdir $pub
  if ($LASTEXITCODE -ne 0) {
    throw "assemble_full_ebook.py failed (exit code $LASTEXITCODE)"
  }
} else {
  Write-Host "WARN: assemble_full_ebook.py not found (skipping combined ebook assembly)"
}

# ---------- 6) Copy full asset folders into the print bundle (recommended) ----------
$assetRoot = Join-Path $pub "assets"
New-Item -ItemType Directory -Force -Path $assetRoot | Out-Null

$assetFolders = @(
  @{ src = ".\outputs\fair_assets";        dst = (Join-Path $assetRoot "fair_assets") },
  @{ src = ".\outputs\draft_paper_assets"; dst = (Join-Path $assetRoot "draft_paper_assets") },
  @{ src = ".\outputs\figures";           dst = (Join-Path $assetRoot "figures") }
)

foreach ($a in $assetFolders) {
  if (Test-Path $a.src) {
    Write-Host "Copying folder $($a.src) -> $($a.dst)"
    Copy-Item $a.src $a.dst -Recurse -Force
  } else {
    Write-Host "WARN: asset folder not found (skipping) $($a.src)"
  }
}

# ---------- 7) Watermark figures LAST (optional; runs only if tool exists) ----------
$wmToolCandidates = @(
  ".\tools\watermark_figures.py",
  ".\sweep_up\inbox\watermark_figures.py"
)

$wmTool = $wmToolCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$figDir = Join-Path $assetRoot "figures"

# Hardcoded brand assets (these exist in your tree)
$logoCol   = Join-Path $ProjectRoot "assets\branding\Final-logomark.png"
$logoWhite = Join-Path $ProjectRoot "assets\brand\final_logo_white.png"

if ($null -ne $wmTool -and (Test-Path $figDir)) {
  if (-not (Test-Path $logoCol)) { throw "Missing logo_col PNG at: $logoCol" }
  if (-not (Test-Path $logoWhite)) { throw "Missing logo_white PNG at: $logoWhite" }

  Write-Host "`nWatermarking figures in: $figDir"
  & $Python (Join-Path $ProjectRoot $wmTool.TrimStart(".\")) `
    --root $figDir `
    --logo_col $logoCol `
    --logo_white $logoWhite `
    --logo_corner tr `
    --tm_corner br `
    --use_white_on_dark

  if ($LASTEXITCODE -ne 0) {
    throw "watermark_figures.py failed (exit code $LASTEXITCODE)"
  }
} else {
  if ($null -eq $wmTool) { Write-Host "WARN: watermark_figures.py not found (skipping watermark)" }
  if (-not (Test-Path $figDir)) { Write-Host "WARN: figures folder not found at $figDir (skipping watermark)" }
}




Write-Host "`nDONE."
Write-Host "Archived prior outputs: .\outputs_archive_$stamp"
Write-Host "Publication bundle:     $pub"
Write-Host "Full bundle path:       $((Resolve-Path $pub).Path)"
if (Test-Path (Join-Path $pub "index.html")) {
  Write-Host "Open combined ebook:    $((Resolve-Path (Join-Path $pub 'index.html')).Path)"
}
