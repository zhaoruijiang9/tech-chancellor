param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('enable', 'disable')]
    [string]$State
)

$managedRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$controlPath = Join-Path $managedRoot 'manifests\control.json'
$control = Get-Content -LiteralPath $controlPath -Raw | ConvertFrom-Json
$control.enabled = $State -eq 'enable'
$control.disabled_reason = if ($control.enabled) { '' } else { 'disabled by PTI rollback control' }
$control | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $controlPath -Encoding UTF8
Write-Output (ConvertTo-Json $control -Compress)
