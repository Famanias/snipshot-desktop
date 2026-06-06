; SnipShot Inno Setup Script
; Build installer using Inno Setup Compiler

#define MyAppName "SnipShot"
#define MyAppVersion "2.0.3"
#define MyAppPublisher "SnipShot"
#define MyAppURL "https://github.com/Famanias/snipshot-desktop"
#define MyAppExeName "SnipShot.exe"

[Setup]
AppId={{68E68754-C3B2-4F15-8AC2-72DF2A478EF6}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=SnipShot_Setup_{#MyAppVersion}
SetupIconFile=resources\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Required: user must accept license before proceeding
LicenseFile=LICENSE.rtf

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\SnipShot\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; ---------------------------------------------------------------------------
; Custom pages: Privacy Notice (shown after the EULA license page)
; ---------------------------------------------------------------------------
[Code]

var
  PrivacyPage: TOutputMsgWizardPage;

procedure InitializeWizard();
begin
  // --- Privacy & Data Notice page ---
  PrivacyPage := CreateOutputMsgPage(
    wpLicense,
    'Privacy Notice & Data Practices',
    'Please read the following important information about SnipShot.',
    'SnipShot' + #13#10 + #13#10 +
    'WHAT THIS SOFTWARE DOES' + #13#10 +
    'SnipShot monitors your screen activity to detect and capture screenshots ' +
    'automatically. Captured images are stored locally on your device and/or ' +
    'uploaded to destinations you configure.' + #13#10 + #13#10 +
    'DATA COLLECTION & PRIVACY' + #13#10 +
    '- SnipShot does NOT collect personal data or transmit screenshots to ' +
    'SnipShot servers.' + #13#10 +
    '- All captured screenshots remain under your control.' + #13#10 +
    '- Upload destinations (e.g. cloud storage) are configured solely by you.' + #13#10 +
    '- Diagnostic/crash data may be collected only if you explicitly opt in.' + #13#10 + #13#10 +
    'PERMISSIONS USED' + #13#10 +
    '- Screen capture access: required to detect and record screenshots.' + #13#10 +
    '- File system access: required to save captured images locally.' + #13#10 +
    '- Network access: required only when uploading to a destination you choose.' + #13#10 + #13#10 +
    'By clicking Next you acknowledge that you have read and understood this ' +
    'Privacy Notice.'
  );
end;

// Validate that the user has scrolled through / accepted the privacy page
// (Inno Setup already enforces the license acceptance via the LicenseFile
// directive, so here we just let Next proceed normally.)
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = PrivacyPage.ID then
  begin
    // Nothing extra required — user clicked Next, that is acknowledgement.
    Result := True;
  end;
end;
