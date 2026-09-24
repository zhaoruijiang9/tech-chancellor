param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
$resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$launcherName = "$([char]0x6253)$([char]0x5f00)$([char]0x6280)$([char]0x672f)$([char]0x4e1e)$([char]0x76f8).cmd"
$shortcutName = "$([char]0x6280)$([char]0x672f)$([char]0x4e1e)$([char]0x76f8).lnk"
$launcher = Join-Path $resolvedRoot $launcherName
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "Canonical launcher not found: $launcher"
}

$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
if (-not $desktop) {
    throw "Windows Desktop known folder could not be resolved."
}

$shortcutPath = Join-Path $desktop $shortcutName
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $resolvedRoot
$shortcut.Description = "TechChancellor local control center"
$shortcut.WindowStyle = 7
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,21"
$shortcut.Save()

Write-Output $shortcutPath
