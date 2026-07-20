# game_snap.ps1 -- capture the running FF9 window to a PNG (the in-game visual feedback loop).
#
# The agent cannot see the running game directly; this closes most of that gap with static
# frames: run it while FF9 is up (windowed/borderless) and Read the PNG. PrintWindow with
# PW_RENDERFULLCONTENT (Win8.1+) captures DirectX content even when partly covered; if it
# fails we fall back to a screen-region copy (window must then be visible and uncovered).
#
#   powershell -File tools\game_snap.ps1 [-OutPath shot.png] [-ProcessName FF9]
param(
    [string]$OutPath = "$env:TEMP\ff9_snap.png",
    [string]$ProcessName = "FF9"
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Snap {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
[Win32Snap]::SetProcessDPIAware() | Out-Null

$p = Get-Process -Name $ProcessName | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $p) { throw "no '$ProcessName' process with a window found -- is the game running?" }
$h = $p.MainWindowHandle
if ([Win32Snap]::IsIconic($h)) { throw "the $ProcessName window is MINIMIZED -- restore it first (capture needs a rendered window)." }

$rect = New-Object Win32Snap+RECT
[Win32Snap]::GetWindowRect($h, [ref]$rect) | Out-Null
$w = $rect.Right - $rect.Left
$hh = $rect.Bottom - $rect.Top
if ($w -le 0 -or $hh -le 0) { throw "degenerate window rect ${w}x${hh}" }

$bmp = New-Object System.Drawing.Bitmap $w, $hh
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$ok = [Win32Snap]::PrintWindow($h, $hdc, 2)    # 2 = PW_RENDERFULLCONTENT (DX/GL content)
$g.ReleaseHdc($hdc)
if (-not $ok) { $g.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bmp.Size) }
$g.Dispose()

# An all-black frame usually means PrintWindow "succeeded" without content (exclusive
# fullscreen). Detect it so the caller gets a diagnosis instead of a useless image.
$sampleDark = $true
foreach ($pt in @(@(50,50), @([int]($w/2),[int]($hh/2)), @(($w-50),($hh-50)), @([int]($w/4),[int]($hh*3/4)))) {
    $c = $bmp.GetPixel($pt[0], $pt[1])
    if ($c.R -gt 12 -or $c.G -gt 12 -or $c.B -gt 12) { $sampleDark = $false; break }
}
$bmp.Save($OutPath, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
if ($sampleDark) {
    Write-Output "saved $OutPath (${w}x${hh}) -- WARNING: sampled pixels are all near-black. If the scene isn't actually dark, the game is likely in EXCLUSIVE fullscreen; switch it to windowed/borderless."
} else {
    Write-Output "saved $OutPath (${w}x${hh})"
}
