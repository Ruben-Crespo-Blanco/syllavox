#ifndef AppVersion
#define AppVersion "0.5.0"
#endif

#ifndef SourceDir
#define SourceDir "..\build\portable\Syllavox"
#endif

#ifndef OutputDir
#define OutputDir "..\build\installer"
#endif

[Setup]
AppId={{A0A7E0D4-DC8E-4E86-AFC7-2EA938F97491}
AppName=Syllavox
AppVersion={#AppVersion}
AppPublisher=Ruben Crespo Blanco
AppPublisherURL=https://github.com/Ruben-Crespo-Blanco/syllavox
AppSupportURL=https://github.com/Ruben-Crespo-Blanco/syllavox/issues
AppUpdatesURL=https://github.com/Ruben-Crespo-Blanco/syllavox/releases
DefaultDirName={localappdata}\Programs\Syllavox
DefaultGroupName=Syllavox
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=Syllavox-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayName=Syllavox
UninstallDisplayIcon={app}\Syllavox.exe
VersionInfoCompany=Ruben Crespo Blanco
VersionInfoDescription=Syllavox offline text-to-speech application
VersionInfoProductName=Syllavox
VersionInfoProductVersion={#AppVersion}
VersionInfoVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Syllavox"; Filename: "{app}\Syllavox.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Syllavox"; Filename: "{app}\Syllavox.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Syllavox.exe"; Description: "Launch Syllavox"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
const
  StartupRegistrySubkey = 'Software\Microsoft\Windows\CurrentVersion\Run';
  StartupValueName = 'Syllavox';

var
  RemoveUserData: Boolean;

function InitializeUninstall(): Boolean;
begin
  RemoveUserData := False;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDataPath: String;
begin
  if CurUninstallStep = usUninstall then begin
    RegDeleteValue(HKCU, StartupRegistrySubkey, StartupValueName);

    UserDataPath := ExpandConstant('{localappdata}\Syllavox');
    if DirExists(UserDataPath) then
      RemoveUserData := MsgBox(
        'Remove Syllavox settings, logs, temporary audio, and downloaded voices as well?'#13#10#13#10 +
        'Choose No to keep them for a future installation.',
        mbConfirmation,
        MB_YESNO
      ) = IDYES;
  end;

  if (CurUninstallStep = usPostUninstall) and RemoveUserData then begin
    UserDataPath := ExpandConstant('{localappdata}\Syllavox');
    DelTree(UserDataPath, True, True, True);
  end;
end;
