; Offline installer: everything (Python, madmom, FFmpeg libraries, Qt) is inside, nothing is downloaded.
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6C7B1E2A-3F4D-4C9B-9A51-5C1A7D2E8B30}
AppName=Click Studio
AppVersion={#AppVersion}
AppPublisher=Max
AppVerName=Click Studio {#AppVersion}
DefaultDirName={autopf}\Click Studio
DefaultGroupName=Click Studio
DisableProgramGroupPage=yes
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=ClickStudio-Setup-{#AppVersion}
SetupIconFile=..\resources\AppIcon.ico
UninstallDisplayIcon={app}\Click Studio.exe
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Click Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Click Studio"; Filename: "{app}\Click Studio.exe"
Name: "{autodesktop}\Click Studio"; Filename: "{app}\Click Studio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Click Studio.exe"; Description: "{cm:LaunchProgram,Click Studio}"; Flags: nowait postinstall skipifsilent
