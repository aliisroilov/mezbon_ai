# ================================================================
#  Mezbon AI Kiosk — Set Display to Portrait Mode (1080x1920)
#  Run as Administrator
# ================================================================

Write-Host "Setting display to portrait mode (1080x1920)..." -ForegroundColor Cyan

# Method 1: Use display settings via registry
# Portrait = 90 degree rotation (orientation value = 1)
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Video"

# Try to set via PowerShell display cmdlets
try {
    # Use CCD API via Add-Type for display rotation
    Add-Type @"
using System;
using System.Runtime.InteropServices;

public class DisplayRotation {
    [DllImport("user32.dll")]
    public static extern int EnumDisplaySettings(string deviceName, int modeNum, ref DEVMODE devMode);

    [DllImport("user32.dll")]
    public static extern int ChangeDisplaySettings(ref DEVMODE devMode, int flags);

    [StructLayout(LayoutKind.Sequential)]
    public struct DEVMODE {
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
        public string dmDeviceName;
        public short dmSpecVersion;
        public short dmDriverVersion;
        public short dmSize;
        public short dmDriverExtra;
        public int dmFields;
        public int dmPositionX;
        public int dmPositionY;
        public int dmDisplayOrientation;
        public int dmDisplayFixedOutput;
        public short dmColor;
        public short dmDuplex;
        public short dmYResolution;
        public short dmTTOption;
        public short dmCollate;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
        public string dmFormName;
        public short dmLogPixels;
        public int dmBitsPerPel;
        public int dmPelsWidth;
        public int dmPelsHeight;
        public int dmDisplayFlags;
        public int dmDisplayFrequency;
        public int dmICMMethod;
        public int dmICMIntent;
        public int dmMediaType;
        public int dmDitherType;
        public int dmReserved1;
        public int dmReserved2;
        public int dmPanningWidth;
        public int dmPanningHeight;
    }

    public const int ENUM_CURRENT_SETTINGS = -1;
    public const int CDS_UPDATEREGISTRY = 0x01;
    public const int CDS_TEST = 0x02;
    public const int DISP_CHANGE_SUCCESSFUL = 0;
    public const int DM_DISPLAYORIENTATION = 0x80;
    public const int DM_PELSWIDTH = 0x80000;
    public const int DM_PELSHEIGHT = 0x100000;

    // Orientation: 0 = Landscape, 1 = Portrait, 2 = Landscape (flipped), 3 = Portrait (flipped)
    public static bool SetPortrait() {
        DEVMODE dm = new DEVMODE();
        dm.dmSize = (short)Marshal.SizeOf(typeof(DEVMODE));

        if (EnumDisplaySettings(null, ENUM_CURRENT_SETTINGS, ref dm) != 0) {
            // If already in landscape (width > height), rotate to portrait
            if (dm.dmPelsWidth > dm.dmPelsHeight) {
                int temp = dm.dmPelsWidth;
                dm.dmPelsWidth = dm.dmPelsHeight;
                dm.dmPelsHeight = temp;
                dm.dmDisplayOrientation = 1; // Portrait (90 degrees)
                dm.dmFields = DM_DISPLAYORIENTATION | DM_PELSWIDTH | DM_PELSHEIGHT;

                int result = ChangeDisplaySettings(ref dm, CDS_UPDATEREGISTRY);
                return result == DISP_CHANGE_SUCCESSFUL;
            }
            return true; // Already portrait
        }
        return false;
    }
}
"@

    $result = [DisplayRotation]::SetPortrait()
    if ($result) {
        Write-Host "Display set to portrait mode successfully!" -ForegroundColor Green
    } else {
        Write-Host "Could not change display orientation. Please set it manually:" -ForegroundColor Yellow
        Write-Host "  Settings > System > Display > Display orientation > Portrait" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Please set display orientation manually:" -ForegroundColor Yellow
    Write-Host "  Settings > System > Display > Display orientation > Portrait" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "If the display looks incorrect, you can revert by running:" -ForegroundColor Gray
Write-Host "  Settings > System > Display > Display orientation > Landscape" -ForegroundColor Gray
