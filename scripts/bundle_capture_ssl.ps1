<#
.SYNOPSIS
    Unified script to build a complete CA bundle for Azure CLI + Azure OpenAI.
    - Exports corporate root + intermediate CAs from Windows
    - Captures live TLS certificates from Azure + OpenAI endpoints
    - Deduplicates all certificates
    - Builds a combined CA bundle
    - Sets REQUESTS_CA_BUNDLE
    - Tests all endpoints
    No OpenSSL required.
#>

param(
    [string]$AzureOpenAIResource = ""
)

Write-Host "=== Building Azure CA Bundle (Unified Script, No OpenSSL) ===" -ForegroundColor Cyan

# --- Directories ---
$BaseDir = "$HOME\.az-ca"
$CapturedDir = Join-Path $BaseDir "captured"
$UniqueDir = Join-Path $BaseDir "unique"
$Bundle = Join-Path $BaseDir "azure-ca-bundle.pem"

New-Item -ItemType Directory -Force -Path $BaseDir | Out-Null
New-Item -ItemType Directory -Force -Path $CapturedDir | Out-Null
New-Item -ItemType Directory -Force -Path $UniqueDir | Out-Null

# --- Helper: Convert Windows cert to PEM ---
function Convert-CertToPem {
    param(
        [System.Security.Cryptography.X509Certificates.X509Certificate2]$Cert,
        [string]$Path
    )

    $pem = @(
        "-----BEGIN CERTIFICATE-----"
        [System.Convert]::ToBase64String($Cert.RawData, 'InsertLineBreaks')
        "-----END CERTIFICATE-----"
    )
    $pem | Set-Content -Encoding ascii $Path
}

# --- Step 1: Export corporate CAs ---
Write-Host "`nExporting corporate root + intermediate CAs..." -ForegroundColor Yellow

$roots = Get-ChildItem Cert:\LocalMachine\Root
$intermediates = Get-ChildItem Cert:\LocalMachine\CA

$allCertFiles = @()

foreach ($cert in $roots + $intermediates) {
    if ($cert.Subject -match "Microsoft|DigiCert|GlobalSign|Google|Apple|Amazon") {
        continue
    }

    $pemPath = Join-Path $BaseDir ("corp-" + $cert.Thumbprint + ".pem")
    Convert-CertToPem -Cert $cert -Path $pemPath
    $allCertFiles += $pemPath
}

# --- Step 2: Capture live TLS certificates ---
function Capture-TLSCert {
    param([string]$Url)

    Write-Host "Capturing TLS certificates from $Url" -ForegroundColor Cyan

    try {
        $req = [System.Net.HttpWebRequest]::Create($Url)
        $req.Method = "GET"
        $req.Timeout = 5000
        $req.AllowAutoRedirect = $false
        $resp = $req.GetResponse()
    }
    catch {
        $resp = $_.Exception.Response
    }

    $cert = $req.ServicePoint.Certificate
    $chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
    $chain.Build($cert) | Out-Null

    $i = 0
    foreach ($element in $chain.ChainElements) {
        $pemPath = Join-Path $CapturedDir ("captured-" + ($Url.Replace("https://","").Replace("/","_")) + "-$i.pem")

        $pem = @(
            "-----BEGIN CERTIFICATE-----"
            [Convert]::ToBase64String($element.Certificate.RawData, 'InsertLineBreaks')
            "-----END CERTIFICATE-----"
        )

        $pem | Set-Content -Encoding ascii $pemPath
        $allCertFiles += $pemPath
        $i++
    }
}

# Azure CLI endpoints
$azureCliEndpoints = @(
    "https://login.microsoftonline.com",
    "https://management.azure.com",
    "https://graph.microsoft.com",
    "https://portal.azure.com"
)

# Azure OpenAI endpoints
$azureOpenAIEndpoints = @("https://api.openai.com")

if ($AzureOpenAIResource -ne "") {
    $azureOpenAIEndpoints += "https://$AzureOpenAIResource.openai.azure.com"
    $azureOpenAIEndpoints += "https://$AzureOpenAIResource.cognitiveservices.azure.com"
}

foreach ($url in $azureCliEndpoints + $azureOpenAIEndpoints) {
    Capture-TLSCert -Url $url
}

# --- Step 3: Deduplicate ---
Write-Host "`nDeduplicating certificates..." -ForegroundColor Yellow

$hashes = @{}

foreach ($file in $allCertFiles) {
    $content = Get-Content $file -Raw
    $hash = (Get-FileHash -InputStream ([IO.MemoryStream]::new([Text.Encoding]::ASCII.GetBytes($content)))).Hash

    if (-not $hashes.ContainsKey($hash)) {
        $hashes[$hash] = $file
        Copy-Item $file (Join-Path $UniqueDir (Split-Path $file -Leaf)) -Force
    }
}

# --- Step 4: Build final bundle (certifi defaults + captured CAs) ---
Write-Host "Building CA bundle at $Bundle" -ForegroundColor Green
$certifiPath = (python -c "import certifi; print(certifi.where())").Trim()
if (Test-Path $certifiPath) {
    Write-Host "Including certifi default CAs from $certifiPath" -ForegroundColor Yellow
    Get-Content $certifiPath | Set-Content $Bundle
    Get-Content (Get-ChildItem $UniqueDir -Filter *.pem) | Add-Content $Bundle
} else {
    Write-Host "certifi not found, using captured CAs only" -ForegroundColor Yellow
    Get-Content (Get-ChildItem $UniqueDir -Filter *.pem) | Set-Content $Bundle
}

# --- Step 5: Set environment variable ---
Write-Host "Setting REQUESTS_CA_BUNDLE..."
$env:REQUESTS_CA_BUNDLE = $Bundle
setx REQUESTS_CA_BUNDLE $Bundle | Out-Null

# --- Step 6: Test endpoints ---
Write-Host "`nTesting all endpoints..." -ForegroundColor Cyan

foreach ($url in $azureCliEndpoints + $azureOpenAIEndpoints) {
    try {
        Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10 | Out-Null
        Write-Host "OK: $url" -ForegroundColor Green
    }
    catch {
        # An HTTP error response (4xx/5xx) still means TLS succeeded
        if ($_.Exception.Response) {
            $code = [int]$_.Exception.Response.StatusCode
            Write-Host "OK: $url (HTTP $code - TLS handshake succeeded)" -ForegroundColor Green
        }
        else {
            Write-Host "FAIL: $url - $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Write-Host "`nDone. Try running: az login" -ForegroundColor Green
