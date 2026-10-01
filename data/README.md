# Local data setup

Downloaded datasets, generated training files, and model-run artifacts stay
local and are ignored by Git. This keeps the repository small, respects the
upstream dataset license, and prevents generated evaluation results from being
mistaken for source code.

A fresh clone should reconstruct the required assets using the setup script
below.

Prerequisites are Windows PowerShell 5.1 or PowerShell 7 and enough temporary
disk space for the BIRD development archive and its extracted contents. The
optional training-asset path also requires
[`uv`](https://docs.astral.sh/uv/) so the script can perform the pinned YAML-to-JSON conversion.

## Quick start on Windows

From the repository root, run **one** of these commands in PowerShell:

```powershell
# Core evaluation database, FINCH questions, and financial metadata.
.\scripts\setup_data.ps1

# Or: prepare the core assets plus the databases used to design SFT data.
.\scripts\setup_data.ps1 -IncludeTrainingAssets
```

If PowerShell blocks local scripts for the current process:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_data.ps1
```

The script:

1. downloads `finch_dataset.json` from the FINCH Hugging Face repository;
2. downloads the official BIRD development bundle;
3. extracts only the persistent files used by DomainAdapt;
4. places them in the paths expected by the notebooks;
5. validates the pinned SHA-256 fingerprints; and
6. removes the temporary archive and extraction directories.

The BIRD download and extraction can temporarily use several hundred
megabytes. Only the small subset listed below is retained after a successful
run.

Use `-KeepDownloads` if you want to retain the upstream archives, or `-Force`
to download and extract them again.

## Core assets

Milestones 0–6 and the evaluation notebooks use:

```text
data/
  financial.sqlite
  finch_dataset.json
  financial_metadata/
    database_description/
      account.csv
      card.csv
      client.csv
      disp.csv
      district.csv
      loan.csv
      order.csv
      trans.csv
  runs/                         # generated locally
```

Pinned fingerprints:

| Asset | SHA-256 |
|---|---|
| `finch_dataset.json` | `c1e462743e4891fecf0fc10dbc6b0eb554fac56a186bdeedec9ccd662e0a4130` |
| `financial.sqlite` | `d15d89cdb068a202b6f2b99342af44dffc1d52545b39ceaf62efdc0ba570101e` |
| Eight financial metadata CSVs, combined | `3f7be83f3f9bdba77d27a66ad38b1a81b3a40361168780f54ceedd985db5fc23` |

The combined metadata hash includes each sorted filename and its exact bytes,
matching the validation in `05_context_engineering.ipynb`.

## Training-data assets

Milestone 7 additionally uses:

```text
data/
  training_databases/
    tables.json
    debit_card_specializing/
      debit_card_specializing.sqlite
    regional_sales/
      regional_sales.sqlite
    retail_world/
      retail_world.sqlite
    sales/
      sales.sqlite
  training/                     # generated locally
```

The setup script validates these database fingerprints:

| Database | SHA-256 |
|---|---|
| `debit_card_specializing` | `b3d149ad05746dbbe5116e229e17e18f09c39db43cf117d9ef3441753608b691` |
| `regional_sales` | `a098eb5b179d3e4441197e51e3f7eb0b8536093da973a20d158e1d6a2e62d4d8` |
| `retail_world` | `1fa03e1c8a3151722d515da21b2de92b2be30fcd854660abf9314303fa0c3862` |
| `sales` | `632673acfed3a90241f8992324755fdd5304d282fe26a97db551bab7dfafce8a` |

`retail_world` is downloaded deliberately but rejected by the notebook's asset
validation because its metadata omits the `Territories` table and
`Employees.HireDate`. Keeping that rejection demonstrates that asset quality
must be verified before individual training examples are trusted.

`tables.json` is deterministically generated from FINCH's pinned
`schemas/database_schemas.yaml` file because FINCH publishes the schema catalog
as YAML while the Milestone 7 notebook consumes the equivalent JSON structure.

## Generated assets are not downloaded

The following directories are created by the notebooks and should not be
copied from somebody else's run:

```text
data/runs/
data/training/
```

They contain model outputs, evaluation receipts, curated records, JSONL files,
and manifests. Recreating them preserves provenance between the local data,
configuration hashes, model deployment, and reported result.

## Manual core download fallback

If you only need the FINCH question file and do not want to run the complete
script, use the exact PowerShell command below:

```powershell
New-Item -ItemType Directory -Force -Path .\data | Out-Null

Invoke-WebRequest `
  -Uri 'https://huggingface.co/datasets/domyn/FINCH/resolve/main/finch_dataset.json?download=true' `
  -OutFile '.\data\finch_dataset.json'

Get-FileHash .\data\finch_dataset.json -Algorithm SHA256
```

The SQLite database and metadata should still be prepared with
`scripts/setup_data.ps1`; downloading only the JSON is insufficient to run the
evaluation notebooks.

## Upstream sources and license

- [FINCH dataset](https://huggingface.co/datasets/domyn/FINCH)
- [BIRD benchmark](https://bird-bench.github.io/)

FINCH and BIRD are distributed under CC-BY-NC-4.0. Keep downloaded data and
derived training records local, use them for research and education in this
project, and review the upstream license before any other use.

The direct BIRD archive URL is an upstream convenience endpoint. If it changes,
use the official BIRD site and preserve the pinned final-file fingerprints
before accepting replacement assets.
