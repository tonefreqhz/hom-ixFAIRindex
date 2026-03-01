\# Printing / Building the Home@ix publication (reproducible workflow)



This note documents the file structure and the exact commands used to build the publication

output that appears under `publication/print\_\*`. It is intended for repeatability by

co-authors, reviewers, and interested readers.



\## 1. High-level structure



\- `publication/`

&nbsp; - `print\_YYYYMMDD\_HHMMSS/`  

&nbsp;   A self-contained, timestamped snapshot used for a specific release/print run.

&nbsp;   This folder is what you open/share for review.

&nbsp;   - `index.html`  

&nbsp;     The rendered publication output (HTML).

&nbsp;   - `figures/` and/or `outputs/figures/`  

&nbsp;     Generated figures used by the publication.

&nbsp;   - `outputs/draft\_paper\_assets/`, `outputs/fair\_assets/`  

&nbsp;     Additional generated assets (figures/tables) used in the paper/publication.

&nbsp;   - `\_backup\_before\_stamp\_\*/`  

&nbsp;     Auto-created backups made prior to watermarking/stamping (not used in the build).



\## 2. Standard workflow (overview)



1\. Generate/refresh figures and publication assets.

2\. Create or update a new `publication/print\_\*` folder for a release.

3\. Watermark/stamp figures inside that print folder (so the stamp is part of the artefact).

4\. Render/build the publication output (HTML/PDF/etc) from the print folder.

5\. Spot-check output visually (figures render, watermark visible on light/dark backgrounds).

6\. Commit the notes + (optionally) the print artefact references, then tag a release.



\## 3. Commands used (PowerShell)



All commands below are run from the repository root unless stated otherwise.



\### 3.1 Locate the latest print folder

```powershell

$root = "C:\\Users\\peewe\\OneDrive\\Desktop\\homeix"

$pub  = Join-Path $root "publication"

$latestPrint = Get-ChildItem -LiteralPath $pub -Directory -Filter "print\_\*" |

&nbsp; Sort-Object LastWriteTime -Descending |

&nbsp; Select-Object -First 1

$latestPrint.FullName



