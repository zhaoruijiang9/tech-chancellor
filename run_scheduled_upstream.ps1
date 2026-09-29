$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '.')).Path
$state = Join-Path $root 'state'
$python = if (Test-Path (Join-Path $root '.venv\Scripts\python.exe')) { Join-Path $root '.venv\Scripts\python.exe' } elseif (Get-Command python -ErrorAction SilentlyContinue) { (Get-Command python).Source } else { throw 'Python 3 is required.' }
$env:PYTHONUTF8 = '1'

function Invoke-UpstreamAction([string]$action, [string]$stdout, [string]$stderr, [string]$token) {
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $python
    $psi.WorkingDirectory = $root
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.Arguments = '"' + (Join-Path $root 'run.py') + '" ' + $action
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        $psi.EnvironmentVariables['GH_TOKEN'] = $token.Trim()
    }
    $process = [Diagnostics.Process]::Start($psi)
    $out = $process.StandardOutput.ReadToEndAsync()
    $err = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $out.Result | Out-File -LiteralPath (Join-Path $state $stdout) -Append -Encoding utf8
    $err.Result | Out-File -LiteralPath (Join-Path $state $stderr) -Append -Encoding utf8
    return $process.ExitCode
}

try {
    $token = $null
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if ($gh) {
        $token = & $gh.Source auth token 2>$null
        if ($LASTEXITCODE -ne 0) { $token = $null }
    }
    $checkExit = Invoke-UpstreamAction 'check-upstream' 'upstream-check.log' 'upstream-check.error.log' $token
    if ($checkExit -ne 0) { exit $checkExit }
    $reviewExit = Invoke-UpstreamAction 'review-upstream' 'upstream-review.log' 'upstream-review.error.log' $token
    exit $reviewExit
} catch {
    $_.Exception.Message | Out-File -LiteralPath (Join-Path $state 'upstream-check.error.log') -Append -Encoding utf8
    exit 1
}
