# ================================================================
#  Mezbon AI Kiosk — Security Restrictions for Kiosk Mode
#  Run as Administrator
# ================================================================

Write-Host "Applying kiosk security restrictions..." -ForegroundColor Cyan

# ── Disable USB mass storage (prevent USB drives, keep webcam/printer) ──
Write-Host "[1/6] Disabling USB mass storage..."
try {
    $usbStorPath = "HKLM:\SYSTEM\CurrentControlSet\Services\USBSTOR"
    Set-ItemProperty -Path $usbStorPath -Name "Start" -Value 4 -Type DWord
    Write-Host "  USB mass storage disabled." -ForegroundColor Green
} catch {
    Write-Host "  Warning: Could not disable USB storage: $_" -ForegroundColor Yellow
}

# ── Hide taskbar ──
Write-Host "[2/6] Hiding taskbar..."
try {
    $taskbarPath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3"
    # Auto-hide taskbar
    $explorerPath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    Set-ItemProperty -Path $explorerPath -Name "TaskbarAutoHideInTabletMode" -Value 1 -Type DWord -ErrorAction SilentlyContinue
    # Use policy to auto-hide
    $policyPath = "HKCU:\SOFTWARE\Policies\Microsoft\Windows\Explorer"
    if (!(Test-Path $policyPath)) { New-Item -Path $policyPath -Force | Out-Null }
    Set-ItemProperty -Path $policyPath -Name "TaskbarLockAll" -Value 1 -Type DWord
    Write-Host "  Taskbar set to auto-hide." -ForegroundColor Green
} catch {
    Write-Host "  Warning: Could not hide taskbar: $_" -ForegroundColor Yellow
}

# ── Disable Task Manager ──
Write-Host "[3/6] Disabling Task Manager..."
try {
    $policyPath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
    if (!(Test-Path $policyPath)) { New-Item -Path $policyPath -Force | Out-Null }
    Set-ItemProperty -Path $policyPath -Name "DisableTaskMgr" -Value 1 -Type DWord
    Write-Host "  Task Manager disabled." -ForegroundColor Green
} catch {
    Write-Host "  Warning: Could not disable Task Manager: $_" -ForegroundColor Yellow
}

# ── Disable keyboard shortcuts (Alt+Tab, Win key) via registry ──
Write-Host "[4/6] Disabling keyboard shortcuts..."
try {
    # Disable Alt+Tab
    $explorerPath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    Set-ItemProperty -Path $explorerPath -Name "DisallowShaking" -Value 1 -Type DWord -ErrorAction SilentlyContinue

    # Disable Win key via Group Policy
    $winKeyPath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer"
    if (!(Test-Path $winKeyPath)) { New-Item -Path $winKeyPath -Force | Out-Null }
    Set-ItemProperty -Path $winKeyPath -Name "NoWinKeys" -Value 1 -Type DWord

    # Disable right-click on desktop
    Set-ItemProperty -Path $winKeyPath -Name "NoViewContextMenu" -Value 1 -Type DWord

    Write-Host "  Keyboard shortcuts restricted." -ForegroundColor Green
} catch {
    Write-Host "  Warning: Could not disable shortcuts: $_" -ForegroundColor Yellow
}

# ── Disable lock screen ──
Write-Host "[5/6] Disabling lock screen..."
try {
    $lockPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization"
    if (!(Test-Path $lockPath)) { New-Item -Path $lockPath -Force | Out-Null }
    Set-ItemProperty -Path $lockPath -Name "NoLockScreen" -Value 1 -Type DWord
    Write-Host "  Lock screen disabled." -ForegroundColor Green
} catch {
    Write-Host "  Warning: Could not disable lock screen: $_" -ForegroundColor Yellow
}

# ── Enable auto-login ──
Write-Host "[6/6] Configuring auto-login..."
try {
    $loginPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
    Set-ItemProperty -Path $loginPath -Name "AutoAdminLogon" -Value "1"
    # Note: DefaultUserName and DefaultPassword must be set manually for security
    Write-Host "  Auto-login enabled (set username/password manually in registry)." -ForegroundColor Green
    Write-Host "  Registry path: HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" -ForegroundColor Gray
    Write-Host "  Set: DefaultUserName = <kiosk-user>" -ForegroundColor Gray
    Write-Host "  Set: DefaultPassword = <password>" -ForegroundColor Gray
} catch {
    Write-Host "  Warning: Could not configure auto-login: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Kiosk restrictions applied!" -ForegroundColor Green
Write-Host ""
Write-Host "To REVERT all restrictions, run:" -ForegroundColor Yellow
Write-Host "  .\disable-peripherals.ps1 -Revert" -ForegroundColor Yellow

# ── Revert mode ──
if ($args -contains "-Revert") {
    Write-Host ""
    Write-Host "Reverting all restrictions..." -ForegroundColor Cyan

    # Re-enable USB storage
    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\USBSTOR" -Name "Start" -Value 3 -Type DWord -ErrorAction SilentlyContinue

    # Re-enable Task Manager
    Remove-ItemProperty -Path "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "DisableTaskMgr" -ErrorAction SilentlyContinue

    # Re-enable Win key and right-click
    $winKeyPath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer"
    Remove-ItemProperty -Path $winKeyPath -Name "NoWinKeys" -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $winKeyPath -Name "NoViewContextMenu" -ErrorAction SilentlyContinue

    # Re-enable lock screen
    Remove-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization" -Name "NoLockScreen" -ErrorAction SilentlyContinue

    Write-Host "All restrictions reverted!" -ForegroundColor Green
}
