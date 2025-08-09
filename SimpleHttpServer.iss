#define MyAppName "SimpleHttpServer"
#define MyAppVersion "0.0.2"
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
Source: "dist/{#MyAppExeName}"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: replacesameversion
Source: "config.ini"; DestDir: "{app}"
Source: "{#MyWebFolder}/sdc.xml"; DestDir: "{app}/{#MyWebFolder}"
Source: "Enycs_512.ico"; DestDir: "{app}"

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "stop"; Flags: waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Parameters: "remove"; Flags: waituntilterminated


[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--startup delayed install"; Flags: runascurrentuser waituntilterminated; Description: "Installa il servizio in autoavvio"; Tasks: AvvioAutomatico
Filename: "{app}\{#MyAppExeName}"; Parameters: "start"; Flags: runascurrentuser waituntilterminated; Description: "Avvia ora il servizio"; Tasks: AvvioAutomatico
Filename: "{app}\{#MyAppExeName}"; Parameters: "install"; Flags: runascurrentuser waituntilterminated; Description: "Installa il servizio in autoavvio"; Tasks: AvvioManuale

[Icons]
Name: "{group}\config.ini"; Filename: "{app}\config.ini"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{group}\Start {#MyAppDescription}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "start"; IconFilename: "{app}\Enycs_512.ico"; AfterInstall: SetElevationBit('{group}\Start {#MyAppDescription}.lnk')
Name: "{group}\Stop {#MyAppDescription}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "stop"; IconFilename: "{app}\Enycs_512.ico"; AfterInstall: SetElevationBit('{group}\Stop {#MyAppDescription}.lnk')

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: dirifempty; Name: "{#MyAppPublisher}"

[Tasks]
Name: "AvvioManuale"; Description: "Il servizio dovrà essere avviato manualmente"; Flags: exclusive
Name: "AvvioAutomatico"; Description: "Il servizio verrà avviato automaticamente al boot"; Flags: exclusive unchecked

; SetElevationBit procedure link https://stackoverflow.com/a/44082068/1145281

[Code]

procedure SetElevationBit(Filename: string);
var
  Buffer: string;
  Stream: TStream;
begin
  Filename := ExpandConstant(Filename);
  Log('Setting elevation bit for ' + Filename);

  Stream := TFileStream.Create(FileName, fmOpenReadWrite);
  try
    Stream.Seek(21, soFromBeginning);
    SetLength(Buffer, 1);
    Stream.ReadBuffer(Buffer, 1);
    Buffer[1] := Chr(Ord(Buffer[1]) or $20);
    Stream.Seek(-1, soFromCurrent);
    Stream.WriteBuffer(Buffer, 1);
  finally
    Stream.Free;
  end;
end;
