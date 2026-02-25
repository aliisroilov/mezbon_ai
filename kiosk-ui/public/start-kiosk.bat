@echo off
REM Hide Windows taskbar
powershell -command "&{$t=[Runtime.InteropServices.Marshal]::GetFunctionPointerForDelegate((New-Object Action{param()}).Method);$s=Add-Type -MemberDefinition '[DllImport(\"user32.dll\")] public static extern int FindWindow(string a,string b); [DllImport(\"user32.dll\")] public static extern int ShowWindow(int a,int b);' -Name W -PassThru;$h=$s::FindWindow('Shell_TrayWnd','');$s::ShowWindow($h,0)}"

REM Launch Chrome in kiosk mode
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --kiosk ^
  --start-fullscreen ^
  --disable-session-crashed-bubble ^
  --noerrdialogs ^
  --disable-infobars ^
  --disable-translate ^
  --no-first-run ^
  --fast ^
  --fast-start ^
  --disable-features=TranslateUI ^
  --overscroll-history-navigation=0 ^
  http://10.99.0.133:5173
