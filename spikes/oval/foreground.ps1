# THROWAWAY spike S3. Prints "<hwnd> <process name>" each time the foreground window changes.
# Polls, so a steal shorter than one poll (about 15 ms) could be missed. Never logs window titles.
param([int]$ParentPid)

Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Fg {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint processId);
}
'@

$parent = Get-Process -Id $ParentPid
$lastHwnd = $null
while (-not $parent.HasExited) {
  $hwnd = [Fg]::GetForegroundWindow()
  if ($hwnd -ne $lastHwnd) {
    $lastHwnd = $hwnd
    $name = 'none'
    if ($hwnd -ne [IntPtr]::Zero) {
      $procId = [uint32]0
      [void][Fg]::GetWindowThreadProcessId($hwnd, [ref]$procId)
      try { $name = (Get-Process -Id $procId -ErrorAction Stop).ProcessName } catch { $name = 'unknown' }
      $name = "$name pid=$procId"
    }
    [Console]::Out.WriteLine("$hwnd $name")
    [Console]::Out.Flush()
  }
  Start-Sleep -Milliseconds 10
}
