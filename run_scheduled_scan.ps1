$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '.')).Path
$state = Join-Path $root 'state'
$python = if (Test-Path (Join-Path $root '.venv\Scripts\python.exe')) { Join-Path $root '.venv\Scripts\python.exe' } elseif (Get-Command python -ErrorAction SilentlyContinue) { (Get-Command python).Source } else { throw 'Python 3 is required.' }
$env:PYTHONUTF8 = '1'

function Invoke-PtiProcess([string]$file, [string[]]$arguments, [string]$stdout, [string]$stderr) {
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $file
    $psi.WorkingDirectory = $root
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.Arguments = ($arguments -join ' ')
    $process = [Diagnostics.Process]::Start($psi)
    $out = $process.StandardOutput.ReadToEndAsync()
    $err = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $out.Result | Out-File -LiteralPath $stdout -Append -Encoding utf8
    $err.Result | Out-File -LiteralPath $stderr -Append -Encoding utf8
    return $process.ExitCode
}

$scanExit = Invoke-PtiProcess $python @('run.py', 'scan', '--dry-run') (Join-Path $state 'scheduled-scan.log') (Join-Path $state 'scheduled-scan.error.log')
if ($scanExit -ne 0) { exit $scanExit }
$count = & $python (Join-Path $root 'run.py') 'pending-count' 2>$null
if ([int]$count -eq 0) { exit 0 }
$trigger = Start-Process -FilePath 'schtasks.exe' -ArgumentList @('/run', '/tn', '\PersonalTechIntelligence\PTI-Chancellor') -WindowStyle Hidden -Wait -PassThru
exit $trigger.ExitCode
