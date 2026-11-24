#ifndef AppVersion
  #error Pass /DAppVersion=x.y.z (or use scripts/build.py --installer)
#endif

[Setup]
AppId={{B63BB232-9707-4C14-97CE-1821F755B725}
AppName=Muta Converter
AppVersion={#AppVersion}
AppPublisher=Lamerone-net
AppPublisherURL=https://github.com/Lamerone-net/Muta-Converter
DefaultDirName={sd}\Programs\Muta Converter
DisableDirPage=no
UsePreviousAppDir=no
DefaultGroupName=Muta Converter
PrivilegesRequired=admin
OutputDir=..\dist\installer
OutputBaseFilename=Muta-Converter-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\Muta.exe
CloseApplications=yes
CloseApplicationsFilter=Muta.exe,muta-cli.exe
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "contextmenu"; Description: "Aggiungi Muta al menu contestuale dei file"; Flags: checkedonce
Name: "startup"; Description: "Avvia Muta all'accesso a Windows"; Flags: unchecked
Name: "desktopicon"; Description: "Crea un collegamento sul desktop"; Flags: unchecked

[Files]
Source: "..\dist\Muta\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Muta Converter"; Filename: "{app}\Muta.exe"; Parameters: "--preferences"
Name: "{autodesktop}\Muta Converter"; Filename: "{app}\Muta.exe"; Parameters: "--preferences"; Tasks: desktopicon

[Run]
Filename: "{app}\Muta.exe"; Parameters: "shell install"; Tasks: contextmenu; Flags: runhidden waituntilterminated runasoriginaluser
Filename: "{app}\Muta.exe"; Parameters: "autostart enable"; Tasks: startup; Flags: runhidden waituntilterminated runasoriginaluser
Filename: "{app}\Muta.exe"; Parameters: "--tray"; Description: "Avvia Muta Converter nella systray"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
Filename: "{app}\Muta.exe"; Parameters: "uninstall-integration"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "RemoveMutaIntegration"
