[Setup]
AppName=Universal Document Text Extractor
AppVersion=1.0.0
DefaultDirName={autopf}\OCR-Tool
DefaultGroupName=OCR Text Extractor
UninstallDisplayIcon={app}\OCR-Tool.exe
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=dist
OutputBaseFilename=OCR-Tool-Setup

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\OCR-Tool\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\OCR Text Extractor"; Filename: "{app}\OCR-Tool.exe"
Name: "{autodesktop}\OCR Text Extractor"; Filename: "{app}\OCR-Tool.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OCR-Tool.exe"; Description: "{cm:LaunchProgram,OCR Text Extractor}"; Flags: nowait postinstall skipifsilent
