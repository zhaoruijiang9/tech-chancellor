param(
    [ValidateSet('deliver', 'compare')]
    [string]$Mode = 'deliver',
    [ValidateSet('architecture')]
    [string]$Type = 'architecture',
    [Parameter(Mandatory = $true)]
    [string]$InputPath,
    [Parameter(Mandatory = $true)]
    [string]$OutputPath,
    [string]$BasePath,
    [string]$HeadPath,
    [string]$AuthorizationPath,
    [ValidateRange(10, 300)]
    [int]$TimeoutSeconds = 120
)

$managedRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$manifestPath = Join-Path $managedRoot 'manifests\archify.json'
$controlPath = Join-Path $managedRoot 'manifests\control.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$control = Get-Content -LiteralPath $controlPath -Raw | ConvertFrom-Json

function Stop-Safely([string]$message, [int]$code = 78) {
    Write-Error $message
    exit $code
}

if (-not $control.enabled) { Stop-Safely 'Archify controlled trial is disabled.' }
if ($manifest.pinned_commit -ne 'c6519401f7b91b9d43011657880893b0a8955548') { Stop-Safely 'Pinned Archify manifest mismatch.' }

$versionRoot = Join-Path $managedRoot ("versions\" + $manifest.pinned_commit)
$entrypoint = Join-Path $versionRoot 'bin\archify.mjs'
$outputRoot = (Resolve-Path (Join-Path $managedRoot 'outputs')).Path
$tempRoot = (Resolve-Path (Join-Path $managedRoot 'temp')).Path

function Full-Path([string]$value) {
    return [IO.Path]::GetFullPath($value)
}

function Assert-Input([string]$value) {
    $full = Full-Path $value
    if ($full -match '(?i)^D:\\money(?:\\|$)') {
        if (-not $AuthorizationPath) { Stop-Safely 'Protected project access is denied by default; current-task authorization is required.' }
        $auth = Full-Path $AuthorizationPath
        if (-not (Test-Path -LiteralPath $auth -PathType Leaf)) { Stop-Safely 'Current-task authorization receipt is missing.' }
        try { $receipt = Get-Content -LiteralPath $auth -Raw | ConvertFrom-Json } catch { Stop-Safely 'Current-task authorization receipt is invalid.' }
        if ($receipt.capability -ne 'Archify' -or $receipt.target_path.TrimEnd('\') -ine 'D:\money' -or $receipt.access_mode -ne 'READ_ONLY' -or $receipt.purpose -ne 'ARCHITECTURE_ANALYSIS' -or $receipt.output_boundary -ne 'OUTSIDE_TARGET_PROJECT' -or $receipt.authorization_source -ne 'DIRECT_USER_TASK_AUTHORIZATION' -or [string]::IsNullOrWhiteSpace($receipt.task_id) -or [string]::IsNullOrWhiteSpace($receipt.nonce)) { Stop-Safely 'Current-task authorization is not scoped to read-only architecture analysis.' }
        try { if ([DateTimeOffset]::Parse($receipt.expires_at) -le [DateTimeOffset]::UtcNow) { Stop-Safely 'Current-task authorization has expired.' } } catch { Stop-Safely 'Current-task authorization expiry is invalid.' }
    }
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { Stop-Safely "Input file does not exist: $full" }
    return $full
}

function Assert-Output([string]$value) {
    $full = Full-Path $value
    if (-not $full.StartsWith($outputRoot, [StringComparison]::OrdinalIgnoreCase)) { Stop-Safely 'Output must stay inside the PTI-managed Archify output directory.' }
    if ($full -match '(?i)^D:\\money(?:\\|$)') { Stop-Safely 'D:\money is permanently blocked for Archify.' }
    New-Item -ItemType Directory -Force -Path (Split-Path $full) | Out-Null
    return $full
}

$inputFull = Assert-Input $InputPath
$outputFull = Assert-Output $OutputPath
if (-not (Test-Path -LiteralPath $entrypoint -PathType Leaf)) { Stop-Safely 'Pinned Archify entrypoint is missing.' }

$arguments = @()
if ($Mode -eq 'deliver') {
    $arguments = @($entrypoint, 'deliver', $Type, $inputFull, $outputFull, '--quality', 'showcase', '--json')
} else {
    if (-not $BasePath -or -not $HeadPath) { Stop-Safely 'Compare mode requires BasePath and HeadPath.' }
    $baseFull = Assert-Input $BasePath
    $headFull = Assert-Input $HeadPath
    $arguments = @($entrypoint, 'compare', $Type, $baseFull, $headFull, $outputFull, '--quality', 'showcase', '--json')
}

$node = (Get-Command node -ErrorAction Stop).Source
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $node
$psi.WorkingDirectory = $versionRoot
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.Arguments = ($arguments | ForEach-Object { '"' + ([string]$_).Replace('"', '\"') + '"' }) -join ' '
$psi.EnvironmentVariables['ARCHIFY_UPDATE_CHECK_DISABLED'] = '1'
$psi.EnvironmentVariables['ARCHIFY_AUTO_OPEN'] = '0'
$psi.EnvironmentVariables['TMP'] = $tempRoot
$psi.EnvironmentVariables['TEMP'] = $tempRoot

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi
$startedAt = (Get-Date).ToUniversalTime().ToString('o')
if (-not $process.Start()) { Stop-Safely 'Could not start pinned Archify.' 70 }
$finished = $process.WaitForExit($TimeoutSeconds * 1000)
if (-not $finished) {
    try { $process.Kill($true) } catch { }
    $receipt = [ordered]@{ wrapper_status = 'TIMEOUT'; exit_code = 124; mode = $Mode; pinned_commit = $manifest.pinned_commit; started_at = $startedAt; output = $outputFull; network_policy = 'UPDATE_CHECK_DISABLED'; browser_open = $false }
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath ($outputFull + '.pti-receipt.json') -Encoding UTF8
    exit 124
}
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()
$exitCode = $process.ExitCode
$receipt = [ordered]@{
    wrapper_status = if ($exitCode -eq 0) { 'PASS' } else { 'FAIL' }
    exit_code = $exitCode
    mode = $Mode
    type = $Type
    pinned_commit = $manifest.pinned_commit
    started_at = $startedAt
    finished_at = (Get-Date).ToUniversalTime().ToString('o')
    input = $inputFull
    output = $outputFull
    output_exists = Test-Path -LiteralPath $outputFull -PathType Leaf
    network_policy = 'UPDATE_CHECK_DISABLED'
    browser_open = $false
    persistent_process = $false
    stdout = $stdout.Trim()
    stderr = $stderr.Trim()
}
$receipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath ($outputFull + '.pti-receipt.json') -Encoding UTF8
if ($stdout) { Write-Output $stdout }
if ($stderr) { Write-Error $stderr }
exit $exitCode
