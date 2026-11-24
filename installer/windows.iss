#ifndef AppVersion
  #error Pass /DAppVersion=x.y.z (or use scripts/build.py --installer)
#endif

[Setup]
AppId={{B63BB232-9707-4C14-97CE-1821F755B725}
AppName=Muta Converter
AppVersion={#AppVersion}
AppPublisher=WoollySheep
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
SetupIconFile=..\assets\branding\icon.ico
CloseApplications=yes
CloseApplicationsFilter=Muta.exe,muta-cli.exe
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[CustomMessages]
english.ContextMenu=Add Muta to the file context menu
english.Startup=Start Muta when signing in to Windows
english.DesktopIcon=Create a desktop shortcut
english.LaunchTray=Start Muta Converter in the system tray
french.ContextMenu=Ajouter Muta au menu contextuel des fichiers
french.Startup=Démarrer Muta à l'ouverture de session Windows
french.DesktopIcon=Créer un raccourci sur le bureau
french.LaunchTray=Démarrer Muta Converter dans la zone de notification
german.ContextMenu=Muta zum Datei-Kontextmenü hinzufügen
german.Startup=Muta bei der Windows-Anmeldung starten
german.DesktopIcon=Desktop-Verknüpfung erstellen
german.LaunchTray=Muta Converter im Infobereich starten
spanish.ContextMenu=Añadir Muta al menú contextual de archivos
spanish.Startup=Iniciar Muta al iniciar sesión en Windows
spanish.DesktopIcon=Crear un acceso directo en el escritorio
spanish.LaunchTray=Iniciar Muta Converter en la bandeja del sistema
italian.ContextMenu=Aggiungi Muta al menu contestuale dei file
italian.Startup=Avvia Muta all'accesso a Windows
italian.DesktopIcon=Crea un collegamento sul desktop
italian.LaunchTray=Avvia Muta Converter nella systray

[Tasks]
Name: "contextmenu"; Description: "{cm:ContextMenu}"; Flags: checkedonce
Name: "startup"; Description: "{cm:Startup}"; Flags: unchecked
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; Flags: unchecked

[Files]
Source: "..\dist\Muta\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Muta Converter"; Filename: "{app}\Muta.exe"; Parameters: "--preferences"
Name: "{autodesktop}\Muta Converter"; Filename: "{app}\Muta.exe"; Parameters: "--preferences"; Tasks: desktopicon

[Run]
Filename: "{app}\Muta.exe"; Parameters: "configure --language {language}"; Flags: runhidden waituntilterminated runasoriginaluser
Filename: "{app}\Muta.exe"; Parameters: "shell install"; Tasks: contextmenu; Flags: runhidden waituntilterminated runasoriginaluser
Filename: "{app}\Muta.exe"; Parameters: "autostart enable"; Tasks: startup; Flags: runhidden waituntilterminated runasoriginaluser
Filename: "{app}\Muta.exe"; Parameters: "--tray"; Description: "{cm:LaunchTray}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
Filename: "{app}\Muta.exe"; Parameters: "uninstall-integration"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "RemoveMutaIntegration"
