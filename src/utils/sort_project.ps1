param(
  [switch]$Execute,          # run moves for real
  [switch]$VerboseLog        # more console output
)

$root = (Get-Location).Path

function Ensure-Dir($p) { New-Item -ItemType Directory -Force -Path $p | Out-Null }

# --- ensure target dirs exist ---
@(
  "inputs\canonical","inputs\provenance",
  "src\build","src\fair","src\viz","src\paper","src\utils",
  "build\interim","build\processed","build\audit",
  "outputs\figures","outputs\tables","outputs\reports",
  "paper\manuscript","paper\bib","paper\build",
  "archive\runs","archive\legacy",
  "sweep_up\inbox","sweep_up\reviewed","sweep_up\to_delete"
) | ForEach-Object { Ensure-Dir (Join-Path $root $_) }

Ensure-Dir (Join-Path $root "sweep_up")
if (!(Test-Path (Join-Path $root "sweep_up\notes.md"))) {
  New-Item -ItemType File -Force -Path (Join-Path $root "sweep_up\notes.md") | Out-Null
}

# --- exclusions (do not touch) ---
$excludeDirs = @(
  ".git", ".venv",
  "inputs","src","build","outputs","paper","archive","sweep_up"
)

$excludeDirRegex = ($excludeDirs | ForEach-Object { [regex]::Escape($_) }) -join "|"
# excludes any path segment equal to one of the above
$excluded = "(^|\\)($excludeDirRegex)(\\|$)"

# --- plan file ---
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$planPath = Join-Path $root "build\audit\move_plan_$timestamp.csv"
$logPath  = Join-Path $root "build\audit\move_log_$timestamp.txt"

"from,to,reason" | Set-Content -Encoding UTF8 $planPath
"Move log $timestamp`r`nRoot: $root`r`nExecute: $Execute`r`n" | Set-Content -Encoding UTF8 $logPath

function Add-Plan($from, $to, $reason) {
  $line = '"' + $from.Replace('"','""') + '","' + $to.Replace('"','""') + '","' + $reason.Replace('"','""') + '"'
  Add-Content -Encoding UTF8 $planPath $line
  if ($VerboseLog) { Write-Host "$reason :: $from -> $to" }
}

function Safe-Move($from, $to) {
  $toDir = Split-Path -Parent $to
  Ensure-Dir $toDir

  if (Test-Path $to) {
    # avoid overwrite collisions: add suffix
    $base = [IO.Path]::GetFileNameWithoutExtension($to)
    $ext  = [IO.Path]::GetExtension($to)
    $i = 1
    do {
      $alt = Join-Path $toDir ($base + "__dup" + $i + $ext)
      $i++
    } while (Test-Path $alt)
    $to = $alt
  }

  if ($Execute) {
    Move-Item -Force -LiteralPath $from -Destination $to
  }
  return $to
}

# --- classification helpers ---
function LooksLikePaperBuild($name) {
  return ($name -match "paper|manuscript|homeix.*paper|combined_paper|print_|latex|arxiv|preprint")
}
function LooksLikeAudit($name) {
  return ($name -match "audit|event|events|checksum|manifest|provenance|trace|log")
}
function LooksLikeProcessedDerived($name) {
  return ($name -match "features|model_matrix|indicator|fair|components|interim|processed|derived")
}

# --- gather candidates (everything outside the known top-level homes) ---
$items = Get-ChildItem -LiteralPath $root -Recurse -Force |
  Where-Object {
    # skip directories
    -not $_.PSIsContainer
  } |
  Where-Object {
    # skip anything under excluded top-level dirs
    ($_.FullName.Substring($root.Length) -notmatch $excluded)
  }

# --- special case: archive whole folders if they exist in root (publication/print_*, outputs_archive_*) ---
# We handle directories at top-level explicitly
$topDirs = Get-ChildItem -LiteralPath $root -Directory -Force | Where-Object { $_.Name -notmatch "^\." }

foreach ($d in $topDirs) {
  if ($d.Name -like "outputs_archive_*") {
    $dest = Join-Path $root ("archive\runs\" + $d.Name)
    Add-Plan $d.FullName $dest "archive_run_dir"
    if ($Execute) { Move-Item -Force -LiteralPath $d.FullName -Destination $dest }
  }
  if ($d.Name -eq "publication") {
    # move print_* subfolders into archive/runs/
    Get-ChildItem -LiteralPath $d.FullName -Directory -Force -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -like "print_*" } |
      ForEach-Object {
        $dest = Join-Path $root ("archive\runs\" + $_.Name)
        Add-Plan $_.FullName $dest "archive_publication_print_dir"
        if ($Execute) { Move-Item -Force -LiteralPath $_.FullName -Destination $dest }
      }
  }
}

# --- file moves ---
foreach ($f in $items) {
  $name = $f.Name
  $full = $f.FullName
  $ext  = $f.Extension.ToLowerInvariant()

  # Canonical inputs (strict)
  if ($name -ieq "Homeatix housing market model(Sheet1) (4).csv") {
    $to = Join-Path $root "inputs\canonical\homeatix_model.csv"
    Add-Plan $full $to "canonical_homeatix"
    $final = Safe-Move $full $to
    Add-Content -Encoding UTF8 $logPath "Moved: $full -> $final"
    continue
  }
  if ($name -ieq "dwellings_stock_by_tenure_uk_annual.csv") {
    $to = Join-Path $root "inputs\canonical\dwellings_stock_by_tenure_uk_annual.csv"
    Add-Plan $full $to "canonical_dwellings_stock"
    $final = Safe-Move $full $to
    Add-Content -Encoding UTF8 $logPath "Moved: $full -> $final"
    continue
  }

  # Manifests (treat as audit/run metadata)
  if ($name -match "^MANIFEST_.*\.txt$") {
    $to = Join-Path $root ("build\audit\" + $name)
    Add-Plan $full $to "audit_manifest"
    $final = Safe-Move $full $to
    Add-Content -Encoding UTF8 $logPath "Moved: $full -> $final"
    continue
  }

  # Paper source
  if ($ext -eq ".tex") {
    $to = Join-Path $root ("paper\manuscript\" + $name)
    Add-Plan $full $to "paper_tex_source"
    $final = Safe-Move $full $to
    Add-Content -Encoding UTF8 $logPath "Moved: $full -> $final"
    continue
  }
  if ($ext -eq ".bib") {
    $to = Join-Path $root ("paper\bib\" + $name)
    Add-Plan $full $to "paper_bib"
    $final = Safe-Move $full $to
    Add-Content -Encoding UTF8 $logPath "Moved: $full -> $final"
    continue
  }

  # Code
  if ($ext -eq ".py") {
    $bucket =
      if ($name -match "plot|figure|viz|animate") { "src\viz" }
      elseif ($name -match "build|pipeline|extract|transform|load|etl") { "src\build" }
      elseif ($name -match "paper|latex|render") { "src\paper" }
      else { "src\fair" }

    $to = Join-Path $root ($bucket + "\" + $name)
    Add-Plan $full $to "code_python"
    $final = Safe-Move $full $to
    Add-Content -Encoding UTF8 $logPath "Moved: $full -> $final"
    continue
  }
  if ($ext -eq ".ps1") {
    $to = Join-Path $root ("src\build\" + $name)
    Add-Plan $full $to "code_powershell"
    $final = Safe-Move $full $to
    Add-Content -Encoding UTF8 $logPath "Moved: $full -> $final"
    continue
  }

  # Figures / media
  if ($ext -in @(".png",".svg",".jpg",".jpeg",".gif",".mp4",".mov")) {
    $to = Join-Path $root ("outputs\figures\" + $name)
    Add-Plan $full $to "output_figure_media"
    $final = Safe-Move $full $to
    Add-Content -Encoding UTF8 $logPath "Moved: $full -> $final"
    continue
  }

  # Data tables
  if ($ext -eq ".csv") {
    if (LooksLikeAudit($name)) {
      $to = Join-Path $root ("build\audit\" + $name)
      Add-Plan $full $to "build_audit_csv"
    }
    elseif (LooksLikeProcessedDerived($name)) {
      $to = Join-Path $root ("build\processed\" + $name)
      Add-Plan $full $to "build_processed_csv"
    }
    else {
      # unknown CSV: do NOT assume canonical; park it
      $to = Join-Path $root ("sweep_up\inbox\_unknown_csv\" + $name)
      Add-Plan $full $to "unknown_csv_to_sweep"
    }
    $final = Safe-Move $full $to
    Add-Content -Encoding UTF8 $logPath "Moved: $full -> $final"
    continue
  }

  # Paper build artifacts / shareables
  if ($ext -in @(".pdf",".html",".epub",".docx")) {
    if (LooksLikePaperBuild($name)) {
      $to = Join-Path $root ("paper\build\" + $name)
      Add-Plan $full $to "paper_build_artifact"
    } else {
      $to = Join-Path $root ("outputs\reports\" + $name)
      Add-Plan $full $to "report_artifact"
    }
    $final = Safe-Move $full $to
    Add-Content -Encoding UTF8 $logPath "Moved: $full -> $final"
    continue
  }

  # Default: sweep up (preserve relative structure)
  $rel = $full.Substring($root.Length).TrimStart("\")
  $to = Join-Path $root ("sweep_up\inbox\" + $rel)
  Add-Plan $full $to "default_sweep"
  $final = Safe-Move $full $to
  Add-Content -Encoding UTF8 $logPath "Moved: $full -> $final"
}

# Canonical checksums (after moves)
Get-FileHash (Join-Path $root "inputs\canonical\*.csv") -Algorithm SHA256 -ErrorAction SilentlyContinue |
  ForEach-Object { "$($_.Hash) *$($_.Path.Replace($root+'\',''))" } |
  Set-Content -Encoding ascii (Join-Path $root "inputs\provenance\CHECKSUMS.sha256")

Write-Host "Plan: $planPath"
Write-Host "Log : $logPath"
Write-Host "Done. Execute mode was: $Execute"
