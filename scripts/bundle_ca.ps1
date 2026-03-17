<#
.SYNOPSIS
    Builds a CA bundle for Azure CLI + Azure OpenAI by exporting corporate CAs
    from the Windows certificate store. No OpenSSL required.

.USAGE
    ./Build-AzureCABundle.ps1 -AzureOpenAIResource "my-openai-resource"
#>

param(
    [string]$AzureOpenAIResource = ""
)

Write-Host "=== Building Azure CA Bundle (No OpenSSL Required) ===" -ForegroundColor Cyan

# --- Output directory ---
$AzCaDir = "$HOME\.az-ca"
$Bundle  = Join-Path $AzCaDir "azure-ca-bundle.pem"

New-Item -ItemType Directory -Force -Path $AzCaDir | Out-Null

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

# --- Collect corporate CAs ---
Write-Host "Exporting corporate root + intermediate CAs..." -ForegroundColor Yellow

$roots = Get-ChildItem Cert:\LocalMachine\Root
$intermediates = Get-ChildItem Cert:\LocalMachine\CA

$exported = @()

foreach ($cert in $roots + $intermediates) {
    # Skip public CAs
    if ($cert.Subject -match "Microsoft" -or
        $cert.Subject -match "DigiCert" -or
        $cert.Subject -match "GlobalSign" -or
        $cert.Subject -match "Google" -or
        $cert.Subject -match "Apple" -or
        $cert.Subject -match "Amazon") {
        continue
    }

    $pemPath = Join-Path $AzCaDir ("corp-" + $cert.Thumbprint + ".pem")
    Convert-CertToPem -Cert $cert -Path $pemPath
    $exported += $pemPath
}

if ($exported.Count -eq 0) {
    Write-Host "No corporate CA certificates found. You may need to export manually." -ForegroundColor Red
    exit 1
}

# --- Build bundle (certifi defaults + corporate CAs) ---
Write-Host "Building CA bundle at $Bundle" -ForegroundColor Green
$certifiPath = (python -c "import certifi; print(certifi.where())").Trim()
if (Test-Path $certifiPath) {
    Write-Host "Including certifi default CAs from $certifiPath" -ForegroundColor Yellow
    Get-Content $certifiPath | Set-Content $Bundle
    Get-Content $exported | Add-Content $Bundle
} else {
    Write-Host "certifi not found, using corporate CAs only" -ForegroundColor Yellow
    Get-Content $exported | Set-Content $Bundle
}

# --- Set environment variable ---
Write-Host "Setting REQUESTS_CA_BUNDLE for current session..."
$env:REQUESTS_CA_BUNDLE = $Bundle

Write-Host "Persisting REQUESTS_CA_BUNDLE..."
setx REQUESTS_CA_BUNDLE $Bundle | Out-Null

# --- Azure CLI endpoints ---
$azureCliEndpoints = @(
    "https://login.microsoftonline.com",
    "https://management.azure.com",
    "https://graph.microsoft.com",
    "https://portal.azure.com"
)

# --- Azure OpenAI endpoints ---
$azureOpenAIEndpoints = @(
    "https://api.openai.com"
)

if ($AzureOpenAIResource -ne "") {
    $azureOpenAIEndpoints += "https://$AzureOpenAIResource.openai.azure.com"
    $azureOpenAIEndpoints += "https://$AzureOpenAIResource.cognitiveservices.azure.com"
}

# --- Test endpoints ---
Write-Host "`nTesting Azure CLI endpoints..." -ForegroundColor Cyan

foreach ($url in $azureCliEndpoints) {
    try {
        Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10 | Out-Null
        Write-Host "OK: $url" -ForegroundColor Green
    }
    catch {
        Write-Host "FAIL: $url" -ForegroundColor Red
    }
}

Write-Host "`nTesting Azure OpenAI endpoints..." -ForegroundColor Cyan

foreach ($url in $azureOpenAIEndpoints) {
    try {
        Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10 | Out-Null
        Write-Host "OK: $url" -ForegroundColor Green
    }
    catch {
        Write-Host "FAIL: $url" -ForegroundColor Red
    }
}

Write-Host "`nDone. Try running: az login" -ForegroundColor Green
