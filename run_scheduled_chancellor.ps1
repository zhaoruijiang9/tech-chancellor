$ErrorActionPreference = 'Stop'
$root = 'D:\personal-tech-intelligence'
$state = Join-Path $root 'state'
$psi = [Diagnostics.ProcessStartInfo]::new()
$psi.FileName = 'D:\python\python.exe'
$psi.WorkingDirectory = $root
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.Arguments = '"' + (Join-Path $root 'run.py') + '" stage-b'
$process = [Diagnostics.Process]::Start($psi)
$out = $process.StandardOutput.ReadToEndAsync()
$err = $process.StandardError.ReadToEndAsync()
$process.WaitForExit()
$out.Result | Out-File -LiteralPath (Join-Path $state 'chancellor.log') -Append -Encoding utf8
$err.Result | Out-File -LiteralPath (Join-Path $state 'chancellor.error.log') -Append -Encoding utf8
exit $process.ExitCode
