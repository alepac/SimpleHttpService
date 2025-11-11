#define MyAppName "SimpleHttpServer"
#define MyAppVersion "0.0.5"
#define MyAppPublisher "Enycs"
#define MyAppURL "http://www.enycs.com/"
#define MyAppExeName "SimpleHttpServer.exe"
#define MyWebFolder "public"
#define MyLogFolder "log"
#define MyAppDescription "Simple Http Server"
#define MyServiceName "SimpleHttpService"


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
OutputBaseFilename={#MyAppName}-Setup_{#MyAppVersion}
OutputDir=dist
PrivilegesRequired=poweruser

[Files]
Source: "dist/{#MyAppExeName}"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: replacesameversion
Source: "config.ini"; DestDir: "{app}"
Source: "{#MyWebFolder}/sdc.xml"; DestDir: "{app}/{#MyWebFolder}"
Source: "Enycs_512.ico"; DestDir: "{app}"

;[UninstallRun]
;Filename: "{app}\{#MyAppExeName}"; Parameters: "stop"; Flags: waituntilterminated
;Filename: "{app}\{#MyAppExeName}"; Parameters: "remove"; Flags: waituntilterminated


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
Name: "AvvioManuale"; Description: "Il servizio dovr? essere avviato manualmente"; Flags: exclusive
Name: "AvvioAutomatico"; Description: "Il servizio verr? avviato automaticamente al boot"; Flags: exclusive unchecked

[Code]
const
  ServiceName = '{#MyServiceName}';
  NET_FW_SCOPE_ALL = 0;
  NET_FW_IP_VERSION_ANY = 2;

procedure SetFirewallException(AppName,FileName:string);
var
  FirewallObject: Variant;
  FirewallManager: Variant;
  FirewallProfile: Variant;
begin
  try
    FirewallObject := CreateOleObject('HNetCfg.FwAuthorizedApplication');
    FirewallObject.ProcessImageFileName := FileName;
    FirewallObject.Name := AppName;
    FirewallObject.Scope := NET_FW_SCOPE_ALL;
    FirewallObject.IpVersion := NET_FW_IP_VERSION_ANY;
    FirewallObject.Enabled := True;
    FirewallManager := CreateOleObject('HNetCfg.FwMgr');
    FirewallProfile := FirewallManager.LocalPolicy.CurrentProfile;
    FirewallProfile.AuthorizedApplications.Add(FirewallObject);
  except
  end;
end;

procedure RemoveFirewallException( FileName:string );
var
  FirewallManager: Variant;
  FirewallProfile: Variant;
begin
  try
    FirewallManager := CreateOleObject('HNetCfg.FwMgr');
    FirewallProfile := FirewallManager.LocalPolicy.CurrentProfile;
    FireWallProfile.AuthorizedApplications.Remove(FileName);
  except
  end;
end;

function ExecAndCapture(const CmdLine: string; var Output: TExecOutput): Boolean;
var
  ResultCode: Integer;
begin
  Result := ExecAndCaptureOutput('cmd.exe', '/C ' + CmdLine, '', SW_HIDE, ewWaitUntilTerminated, ResultCode, Output);

end;

function IsServiceStopped(): Boolean;
var
  Output: TExecOutput;
  ResultCode: Integer;
begin
  Result := False;
  if ExecAndCapture('sc query "' + ServiceName + '"', Output) then
    Result := (Pos('STOPPED', StringJoin(' ', Output.StdOut)) > 0 );
end;

function WaitForServiceToStop(MaxSeconds: Integer): Boolean;
var
  i: Integer;
begin
  for i := 0 to MaxSeconds do
  begin
    if IsServiceStopped() then
    begin
      Result := True;
      Exit;
    end;
    Sleep(1000);
  end;
  Result := False;
end;

function IsServiceDeleted(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  // Esegui il comando e cattura il codice di ritorno
  // Non è necessario catturare l'output testuale, ma il formato della funzione lo richiede
  Exec('sc.exe', 'query "' + ServiceName + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // Il servizio non esiste se il codice di errore è 1060
  if ResultCode = 1060 then
  begin
    Result := True;
  end;
end;

function StopAndDeleteService(): Boolean;
var
  ResultCode: Integer;
  Success: Boolean;
begin
  Result := True
  
  if not IsServiceDeleted() then
  begin
    // Prova a fermare il servizio
    Exec('sc.exe', 'stop "' + ServiceName + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // Attendi che sia fermo (max 10 secondi)
    Success := WaitForServiceToStop(10);

    // Prova a eliminarlo
    Success := Exec('sc.exe', 'delete "' + ServiceName + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and Success;

    // Verifica che sia stato rimosso
    Success := IsServiceDeleted() and Success;

    Result := Success;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    if not StopAndDeleteService() then
      MsgBox('Impossibile fermare o rimuovere il servizio "' + ServiceName + '". Assicurati di avere i permessi necessari.', mbError, MB_OK);
    RemoveFirewallException(ExpandConstant('{app}\')+'{#MyAppExeName}');
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    if not StopAndDeleteService() then
      MsgBox('Impossibile fermare il servizio. Assicurati di avere i permessi necessari.', mbError, MB_OK);
  end;
  if CurStep=ssPostInstall then
      SetFirewallException('{#MyAppName}', ExpandConstant('{app}\')+'{#MyAppExeName}');
end;

// SetElevationBit procedure link https://stackoverflow.com/a/44082068/1145281
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
