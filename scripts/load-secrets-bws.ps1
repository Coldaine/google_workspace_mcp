param(
  [string]$MappingPath = "$PSScriptRoot/../secrets/bws_map.json"
)

if (-not (Test-Path $MappingPath)) {
  Write-Error "Mapping file not found: $MappingPath"
  exit 2
}

$mapping = Get-Content $MappingPath | ConvertFrom-Json

foreach ($prop in $mapping.PSObject.Properties) {
  $envKey = $prop.Name
  $secretId = $prop.Value
  
  try {
    $json = bws secret get $secretId | ConvertFrom-Json
    if ($json.value) {
        Set-Item -Path "env:$envKey" -Value $json.value
        Write-Host "Set $envKey"
    }
  } catch {
    Write-Error "Failed to fetch $envKey ($secretId): $_"
  }
}
