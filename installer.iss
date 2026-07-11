; =============================================================================
;  Orion School Management System - Inno Setup 6 Installer Script
;  Compile with Inno Setup 6: https://jrsoftware.org/isinfo.php
;
;  How to build the full installer:
;    1. Run:  python build_executable.py
;    2. Open installer.iss in Inno Setup 6 and press F9 (Build > Compile)
;    3. Installer saved to: installer_output\OrionSMS_Setup.exe
;
;  Data storage (database + config):
;    %LOCALAPPDATA%\OrionSMS\   (always user-writable, even on C:\Program Files)
; =============================================================================

#define AppName      "Orion School Management System"
#define AppVersion   "1.0.0"
#define AppPublisher "Orion Education Technologies"
#define AppURL       "https://github.com/Exective-2/Orion-Desktop-School-System"
#define AppExeName   "OrionSchoolManagementSystem.exe"
#define SourceDir    "dist\OrionSchoolManagementSystem"
#define DataFolder   "{localappdata}\OrionSMS"

[Setup]
AppId={{A3F2C1D4-7E8B-4F5A-9C0D-1B2E3F4A5B6C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=no
OutputDir=installer_output
OutputBaseFilename=OrionSMS_Setup
SetupIconFile=assets\sms.ico
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
PrivilegesRequired=admin
MinVersion=10.0
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
DisableProgramGroupPage=no
DisableDirPage=no
DirExistsWarning=auto

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";   Description: "Create a &Desktop shortcut";    GroupDescription: "Additional icons:"; Flags: checkedonce
Name: "startmenuicon"; Description: "Create a &Start Menu shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Dirs]
; Create the user-data folder with write permissions for all users
Name: "{#DataFolder}"; Permissions: users-full

[Files]
; -- Application binaries (install dir = read-only for normal users) --
Source: "{#SourceDir}\*";  DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\sms.ico";  DestDir: "{app}\assets"; Flags: ignoreversion

; -- Seed a clean config.json into the writable user-data folder --
; onlyifdoesntexist ensures we never overwrite an existing school's config
Source: "{#SourceDir}\config.json"; DestDir: "{#DataFolder}"; Flags: ignoreversion onlyifdoesntexist

[Icons]
; Start Menu
Name: "{group}\{#AppName}";             Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\sms.ico"; Tasks: startmenuicon
Name: "{group}\Uninstall {#AppName}";   Filename: "{uninstallexe}"
; Desktop shortcut
Name: "{autodesktop}\{#AppName}";       Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\sms.ico"; Tasks: desktopicon

[Run]
; Offer to launch immediately after install
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove the install folder if empty after uninstall
; NOTE: User data in %LOCALAPPDATA%\OrionSMS\ is intentionally kept
;       so the school database is not lost on reinstall/upgrade
Type: dirifempty; Name: "{app}"

[Code]
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel2.Caption :=
    'This will install ' + ExpandConstant('{#AppName}') + ' version ' +
    ExpandConstant('{#AppVersion}') + ' on your computer.' + #13#10 + #13#10 +
    'You can choose any drive or folder as the installation directory.' + #13#10 +
    'A shortcut will be placed on your Desktop for quick access.' + #13#10 + #13#10 +
    'Your school data (database & settings) will be stored in:' + #13#10 +
    '  %LOCALAPPDATA%\OrionSMS\' + #13#10 + #13#10 +
    'Click Next to continue, or Cancel to exit.';
end;
