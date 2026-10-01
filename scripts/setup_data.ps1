[CmdletBinding()]
param(
    [switch]$IncludeTrainingAssets,
    [switch]$KeepDownloads,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$dataRoot = Join-Path $repoRoot "data"
$downloadRoot = Join-Path $dataRoot ".downloads"
$birdExtractRoot = Join-Path $downloadRoot "bird_dev"
$birdDatabaseRoot = Join-Path $downloadRoot "bird_databases"

New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
New-Item -ItemType Directory -Force -Path $downloadRoot | Out-Null

function Get-DataFile {
    param(
        [Parameter(Mandatory)]
        [string]$Uri,

        [Parameter(Mandatory)]
        [string]$Destination
    )

    if ((Test-Path $Destination) -and -not $Force) {
        Write-Host "Using existing file: $Destination"
        return
    }

    $parent = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null

    Write-Host "Downloading: $Uri"
    Invoke-WebRequest -Uri $Uri -OutFile $Destination
}

function Assert-FileHash {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$ExpectedSha256
    )

    if (-not (Test-Path $Path)) {
        throw "Required file is missing: $Path"
    }

    $actual = (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
    if ($actual -ne $ExpectedSha256.ToLowerInvariant()) {
        throw "SHA-256 mismatch for $Path`nExpected: $ExpectedSha256`nActual:   $actual"
    }

    Write-Host "Validated: $Path"
}

function Find-BirdDatabaseFile {
    param(
        [Parameter(Mandatory)]
        [string]$DatabaseId
    )

    $matches = @(
        Get-ChildItem `
            -Path $birdDatabaseRoot `
            -Recurse `
            -File `
            -Filter "$DatabaseId.sqlite"
    )

    if ($matches.Count -ne 1) {
        throw "Expected one $DatabaseId.sqlite under $birdDatabaseRoot; found $($matches.Count)."
    }

    return $matches[0]
}

function Get-CombinedMetadataHash {
    param(
        [Parameter(Mandatory)]
        [string]$Directory
    )

    $files = @(
        Get-ChildItem -Path $Directory -File -Filter "*.csv" |
            Sort-Object Name
    )

    if ($files.Count -ne 8) {
        throw "Expected 8 metadata CSVs under $Directory; found $($files.Count)."
    }

    $buffer = [System.IO.MemoryStream]::new()
    try {
        foreach ($file in $files) {
            $nameBytes = [System.Text.Encoding]::UTF8.GetBytes($file.Name)
            $buffer.Write($nameBytes, 0, $nameBytes.Length)
            $buffer.WriteByte(0)

            $fileBytes = [System.IO.File]::ReadAllBytes($file.FullName)
            $buffer.Write($fileBytes, 0, $fileBytes.Length)
            $buffer.WriteByte(0)
        }

        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            $digest = $sha.ComputeHash($buffer.ToArray())
            return ([System.BitConverter]::ToString($digest)).Replace("-", "").ToLowerInvariant()
        }
        finally {
            $sha.Dispose()
        }
    }
    finally {
        $buffer.Dispose()
    }
}

$finchDatasetPath = Join-Path $dataRoot "finch_dataset.json"
$birdArchivePath = Join-Path $downloadRoot "bird_dev.zip"

Get-DataFile `
    -Uri "https://huggingface.co/datasets/domyn/FINCH/resolve/main/finch_dataset.json?download=true" `
    -Destination $finchDatasetPath

Get-DataFile `
    -Uri "https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip" `
    -Destination $birdArchivePath

if ($Force -or -not (Test-Path $birdExtractRoot)) {
    if (Test-Path $birdExtractRoot) {
        Remove-Item -Recurse -Force $birdExtractRoot
    }
    New-Item -ItemType Directory -Force -Path $birdExtractRoot | Out-Null
    Write-Host "Extracting BIRD development bundle..."
    Expand-Archive `
        -Path $birdArchivePath `
        -DestinationPath $birdExtractRoot `
        -Force
}

$databaseArchiveMatches = @(
    Get-ChildItem `
        -Path $birdExtractRoot `
        -Recurse `
        -File `
        -Filter "dev_databases.zip"
)

if ($databaseArchiveMatches.Count -ne 1) {
    throw "Expected one dev_databases.zip; found $($databaseArchiveMatches.Count)."
}

if ($Force -or -not (Test-Path $birdDatabaseRoot)) {
    if (Test-Path $birdDatabaseRoot) {
        Remove-Item -Recurse -Force $birdDatabaseRoot
    }
    New-Item -ItemType Directory -Force -Path $birdDatabaseRoot | Out-Null
    Write-Host "Extracting selected BIRD database source bundle..."
    Expand-Archive `
        -Path $databaseArchiveMatches[0].FullName `
        -DestinationPath $birdDatabaseRoot `
        -Force
}

$financialSource = Find-BirdDatabaseFile -DatabaseId "financial"
$financialDestination = Join-Path $dataRoot "financial.sqlite"
Copy-Item -Force $financialSource.FullName $financialDestination

$metadataSource = Join-Path $financialSource.Directory.FullName "database_description"
if (-not (Test-Path $metadataSource)) {
    throw "Financial metadata directory is missing: $metadataSource"
}

$metadataDestination = Join-Path $dataRoot "financial_metadata\database_description"
if (Test-Path $metadataDestination) {
    Remove-Item -Recurse -Force $metadataDestination
}
New-Item -ItemType Directory -Force -Path $metadataDestination | Out-Null
Copy-Item -Force (Join-Path $metadataSource "*.csv") $metadataDestination

Assert-FileHash `
    -Path $finchDatasetPath `
    -ExpectedSha256 "c1e462743e4891fecf0fc10dbc6b0eb554fac56a186bdeedec9ccd662e0a4130"

Assert-FileHash `
    -Path $financialDestination `
    -ExpectedSha256 "d15d89cdb068a202b6f2b99342af44dffc1d52545b39ceaf62efdc0ba570101e"

$metadataHash = Get-CombinedMetadataHash -Directory $metadataDestination
$expectedMetadataHash = "3f7be83f3f9bdba77d27a66ad38b1a81b3a40361168780f54ceedd985db5fc23"
if ($metadataHash -ne $expectedMetadataHash) {
    throw "Financial metadata SHA-256 mismatch.`nExpected: $expectedMetadataHash`nActual:   $metadataHash"
}
Write-Host "Validated financial metadata: $metadataHash"

if ($IncludeTrainingAssets) {
    $trainingRoot = Join-Path $dataRoot "training_databases"
    New-Item -ItemType Directory -Force -Path $trainingRoot | Out-Null

    $databaseHashes = [ordered]@{
        "debit_card_specializing" = "b3d149ad05746dbbe5116e229e17e18f09c39db43cf117d9ef3441753608b691"
        "regional_sales" = "a098eb5b179d3e4441197e51e3f7eb0b8536093da973a20d158e1d6a2e62d4d8"
        "retail_world" = "1fa03e1c8a3151722d515da21b2de92b2be30fcd854660abf9314303fa0c3862"
        "sales" = "632673acfed3a90241f8992324755fdd5304d282fe26a97db551bab7dfafce8a"
    }

    foreach ($databaseId in $databaseHashes.Keys) {
        $source = Find-BirdDatabaseFile -DatabaseId $databaseId
        $destinationDirectory = Join-Path $trainingRoot $databaseId
        $destination = Join-Path $destinationDirectory "$databaseId.sqlite"
        New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null
        Copy-Item -Force $source.FullName $destination
        Assert-FileHash `
            -Path $destination `
            -ExpectedSha256 $databaseHashes[$databaseId]
    }

    $schemaYamlPath = Join-Path $downloadRoot "database_schemas.yaml"
    Get-DataFile `
        -Uri "https://huggingface.co/datasets/domyn/FINCH/resolve/main/schemas/database_schemas.yaml?download=true" `
        -Destination $schemaYamlPath

    Assert-FileHash `
        -Path $schemaYamlPath `
        -ExpectedSha256 "59131dc9fc98522c8f1291a7c94b5e04c5cc89b29e9bf8caa64f8c2cef8d5b62"

    $tablesPath = Join-Path $trainingRoot "tables.json"
    $conversionScript = @'
import json
import sys

import yaml

source_path, destination_path = sys.argv[1:]
with open(source_path, encoding="utf-8") as source:
    metadata = yaml.safe_load(source)
with open(destination_path, "w", encoding="utf-8") as destination:
    json.dump(metadata, destination, indent=2)
    destination.write("\n")
'@

    Write-Host "Converting FINCH schema metadata to tables.json..."
    $conversionScript | uv run --with pyyaml python - $schemaYamlPath $tablesPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to convert FINCH schema metadata to JSON."
    }

    Write-Host "Training metadata SHA-256: $((Get-FileHash -Algorithm SHA256 -Path $tablesPath).Hash.ToLowerInvariant())"
    Write-Host "Milestone 7 database assets are ready."
}

New-Item -ItemType Directory -Force -Path (Join-Path $dataRoot "runs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dataRoot "training") | Out-Null

if (-not $KeepDownloads) {
    Write-Host "Removing temporary BIRD archives and extraction directories..."
    Remove-Item -Recurse -Force $downloadRoot
}

Write-Host "Core DomainAdapt data setup completed successfully."
