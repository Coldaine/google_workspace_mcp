# Bitwarden secrets loader (PowerShell)
# Usage:
#   .\scripts\load-secrets.ps1 | Invoke-Expression
# Prerequisites: bw CLI installed, run `bw login` (if needed) then:
#   $env:BW_SESSION = (bw unlock --raw)

param(
  [string]$MappingPath = "$PSScriptRoot/../secrets/bitwarden_map.json"
)

if (-not $env:BW_SESSION) {
  Write-Error "BW_SESSION not set. Run: $env:BW_SESSION = (bw unlock --raw)"
  exit 1
}

if (-not (Test-Path $MappingPath)) {
  Write-Error "Mapping file not found: $MappingPath"
  exit 2
}

$mapping = Get-Content $MappingPath | ConvertFrom-Json
$placeholders = @()

foreach ($prop in $mapping.PSObject.Properties) {
  $envKey = $prop.Name
  $itemId = $prop.Value.item_id
  $field = $prop.Value.field
  if (-not $itemId -or $itemId -like 'REPLACE-WITH*') {
    $placeholders += $envKey
    continue
  }
  try {
    $json = bw get item $itemId | ConvertFrom-Json
  } catch {
    Write-Warning "Failed to fetch item $itemId for $envKey: $_"
    continue
  }
  $value = $null
  if ($json.fields) {
    foreach ($f in $json.fields) { if ($f.name -eq $field) { $value = $f.value; break } }
  }
  if (-not $value -and $json.login) {
    if ($field -in 'client_id','username','user' -and $json.login.username) { $value = $json.login.username }
    elseif ($field -in 'client_secret','password','secret' -and $json.login.password) { $value = $json.login.password }
  }
  if (-not $value) {
    Write-Warning "Field '$field' not found for item $itemId ($envKey)"
    continue
  }
  # Set in current session
  Set-Item -Path Env:$envKey -Value $value
  Write-Host "Set $envKey" -ForegroundColor Green
}

if ($placeholders.Count -gt 0) {
  Write-Host "Placeholder item IDs not configured for: $($placeholders -join ', ')" -ForegroundColor Yellow
}

Write-Host "Secrets loaded into current PowerShell session." -ForegroundColor Cyan
