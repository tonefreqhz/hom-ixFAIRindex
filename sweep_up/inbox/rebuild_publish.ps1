param(
  [string]$ProjectRoot = "C:\Users\peewe\OneDrive\Desktop\homeix"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location $ProjectRoot

# Require Windows Python launcher
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  throw "Python launcher 'py' not found. Install Python from python.org (recommended) so 'py' is available."
}

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
  "build_forward_indicator.py",
  "choose_calm_baseline.py",
  "compute_fair.py",
  "plot_fair.py",
  "build_fair_outputs.py",
  "make_domain_terms.py",
  "fix_domain_terms.py",
  "backtest_ew_crash_warning.py"
)

foreach ($s in $steps) {
  if (!(Test-Path ".\$s")) { throw "Missing script: $s" }

  Write-Host "`nRunning: $s"
  py ".\$s"

  # HARD STOP if the Python script errored (prevents cascading failures)
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
# Requires assemble_full_ebook.py in the project root (writes index.html into current directory)
if (Test-Path ".\assemble_full_ebook.py") {
  Write-Host "`nAssembling combined full ebook -> $pub\index.html"
  Push-Location $pub
  try {
    py "$ProjectRoot\assemble_full_ebook.py"
    if ($LASTEXITCODE -ne 0) {
      throw "assemble_full_ebook.py failed (exit code $LASTEXITCODE)"
    }
  } finally {
    Pop-Location
  }
} else {
  Write-Host "WARN: .\assemble_full_ebook.py not found (skipping combined ebook assembly)"
}

# ---------- 6) Copy full asset folders into the print bundle (recommended) ----------
# This makes the print bundle self-contained and stable for review.
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

Write-Host "`nDONE."
Write-Host "Archived prior outputs: .\outputs_archive_$stamp"
Write-Host "Publication bundle:     $pub"
Write-Host "Full bundle path:       $((Resolve-Path $pub).Path)"
if (Test-Path (Join-Path $pub "index.html")) {
  Write-Host "Open combined ebook:    $((Resolve-Path (Join-Path $pub 'index.html')).Path)"
}
