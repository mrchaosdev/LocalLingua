#ifndef BundleDir
  #error Pass /DBundleDir=<absolute directory from package-personal.ps1>
#endif
#define AppVersion "0.4.0"
[Setup]
AppId={{BE7CFD01-F2C9-44F2-83C7-5CFCA208163B}
AppName=LocalLingua
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\LocalLingua
DefaultGroupName=LocalLingua
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
OutputBaseFilename=LocalLingua-Setup-{#AppVersion}-win-x64
OutputDir=..\release\installers
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\LocalLingua.Launcher.exe
CloseApplications=yes
RestartApplications=no
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\LocalLingua"; Filename: "{app}\LocalLingua.Launcher.exe"
Name: "{autodesktop}\LocalLingua"; Filename: "{app}\LocalLingua.Launcher.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\LocalLingua.Launcher.exe"; Description: "Open LocalLingua"; Flags: nowait postinstall skipifsilent
[UninstallDelete]
; User model files and preferences under LocalAppData\LocalLingua are retained intentionally.
