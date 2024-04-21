#define MyAppName "SimpleHttpServer"
#define MyAppVersion "0.0.1"
#define MyAppPublisher "Enycs"
#define MyAppURL "http://www.enycs.com/"
#define MyAppExeName "SimpleHttpServer.exe"
#define MyWebFolder "public"
#define MyLogFolder "log"
#define MyAppDescription "Simple Http Server"

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Setup]
AppId={{A07D07FA-5F30-4604-B8CE-D319E3FB1A8E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
WizardStyle=modern
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf64}\{#MyAppPublisher}\{#MyAppName}
DefaultGroupName={#MyAppPublisher}\{#MyAppName}
Compression=lzma2
SolidCompression=yes
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppDescription}
OutputBaseFilename={#MyAppName}-Setup
OutputDir=dist
PrivilegesRequired=poweruser

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: replacesameversion
Source: "config.ini"; DestDir: "{app}"
Source: "{#MyWebFolder}/sdc.xml"; DestDir: "{app}/{#MyWebFolder}"

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "stop"; Flags: waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Parameters: "remove"; Flags: waituntilterminated


[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--startup delayed install"; Flags: postinstall runascurrentuser waituntilterminated; Description: "Installa il servizio in autoavvio"
Filename: "{app}\{#MyAppExeName}"; Parameters: "start"; Flags: postinstall runascurrentuser waituntilterminated; Description: "Avvia ora il servizio"

[Icons]
Name: "{group}\config.ini"; Filename: "{app}\config.ini"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\{#MyWebFolder}"
Type: filesandordirs; Name: "{app}\{#MyLogFolder}"
Type: dirifempty; Name: "{app}"
