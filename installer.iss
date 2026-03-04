; TodoMate Widget - Inno Setup 인스톨러 스크립트
; Inno Setup 6.x 이상 필요

#define MyAppName "TodoMate Widget"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TodoMate Widget"
#define MyAppURL "https://github.com/dydtkddl/todomate-widget"
#define MyAppExeName "TodoMateWidget.exe"

[Setup]
; 앱 고유 ID (GUID) — 한 번 생성 후 변경하지 말 것
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; 바탕화면 바로가기 생성 여부를 사용자에게 물어봄
AllowNoIcons=yes
; 인스톨러 출력 경로
OutputDir=installer_output
OutputBaseFilename=TodoMateWidget_Setup_{#MyAppVersion}
; 인스톨러 자체 아이콘
SetupIconFile=icon.ico
; 압축 설정
Compression=lzma2/ultra64
SolidCompression=yes
; UI 스타일
WizardStyle=modern
; 64비트 모드
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; 관리자 권한 불필요 (사용자 폴더에 설치)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; 언인스톨러
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; 최소 Windows 버전
MinVersion=10.0

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; 바탕화면 아이콘 생성 (기본 체크)
Name: "desktopicon"; Description: "바탕화면에 바로가기 생성(&D)"; GroupDescription: "추가 아이콘:"; Flags: checkedonce
; 시작 시 자동실행
Name: "startup"; Description: "Windows 시작 시 자동 실행(&S)"; GroupDescription: "추가 옵션:"; Flags: unchecked

[Files]
; PyInstaller로 빌드된 exe
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; 아이콘 파일 (바로가기용)
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 시작 메뉴 바로가기
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
; 시작 메뉴에 언인스톨 바로가기
Name: "{group}\{#MyAppName} 제거"; Filename: "{uninstallexe}"; IconFilename: "{app}\icon.ico"
; 바탕화면 바로가기 (사용자가 선택한 경우)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon
; 시작프로그램 (자동실행 선택한 경우)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
; 설치 완료 후 앱 실행 옵션
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} 실행"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 언인스톨 시 앱 데이터도 삭제 (선택적)
Type: filesandordirs; Name: "{localappdata}\pywebview"

[Code]
// 이미 실행 중인 프로세스가 있으면 종료 안내
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// 이미 설치된 경우 업그레이드 안내
function InitializeUninstall(): Boolean;
begin
  Result := True;
end;

