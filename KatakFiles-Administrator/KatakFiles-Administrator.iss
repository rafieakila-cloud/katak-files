[Setup]
AppName=Katak-Files Administrator
AppVersion=1.0.0
AppPublisher=bawapi-katak
DefaultDirName={autopf}\Katak-Files Administrator
DefaultGroupName=Katak-Files Administrator
OutputDir=.
OutputBaseFilename=Katak-Files-Administrator-Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=..\KatakFILES\katak.ico
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\KatakFilesAdministrator.exe

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut:"

[Files]
Source: "dist\KatakFilesAdministrator.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Katak-Files Administrator"; Filename: "{app}\KatakFilesAdministrator.exe"
Name: "{commondesktop}\Katak-Files Administrator"; Filename: "{app}\KatakFilesAdministrator.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\KatakFilesAdministrator.exe"; Description: "Buka Katak-Files Administrator"; Flags: nowait postinstall skipifsilent
