[Setup]
AppName=KatakFILES
AppVersion=0.3.0
AppPublisher=Rafie Akila
AppPublisherURL=https://github.com/rafieakila-cloud/check-the-water
DefaultDirName={autopf}\KatakFILES
DefaultGroupName=KatakFILES
OutputDir=.
OutputBaseFilename=KatakFILES-Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=katak.ico
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\KatakFILES.exe

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut:"

[Files]
Source: "dist\KatakFILES.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\KatakFILES"; Filename: "{app}\KatakFILES.exe"
Name: "{commondesktop}\KatakFILES"; Filename: "{app}\KatakFILES.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\KatakFILES.exe"; Description: "Jalankan KatakFILES"; Flags: nowait postinstall skipifsilent
