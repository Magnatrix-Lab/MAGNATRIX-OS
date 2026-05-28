; MAGNATRIX-OS NSIS Installer Script
; ═══════════════════════════════════
; Build with:  makensis installer.nsi
; Output:      MAGNATRIX-OS-Setup.exe

!define PRODUCT_NAME "MAGNATRIX-OS"
!define PRODUCT_VERSION "0.9.5-alpha"
!define PRODUCT_PUBLISHER "Magnatrix Lab"
!define PRODUCT_WEB_SITE "https://github.com/Magnatrix-Lab/MAGNATRIX-OS"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\MAGNATRIX-OS.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"
!define PRODUCT_STARTMENU_REGVAL "NSIS:StartMenuDir"

; ── MUI Settings ──────────────────────────────────────────────────────────
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; ── Installer Attributes ──────────────────────────────────────────────────
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "..\dist\MAGNATRIX-OS-Setup.exe"
InstallDir "$PROGRAMFILES64\${PRODUCT_NAME}"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show
RequestExecutionLevel admin

; ── Sections ──────────────────────────────────────────────────────────────
Section "MAGNATRIX-OS Core (required)" SEC01
    SectionIn RO
    SetOutPath "$INSTDIR"
    SetOverwrite ifnewer

    ; Copy all files from dist output
    File /r "..\dist\MAGNATRIX-OS\*.*"

    ; Write registry keys
    WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\MAGNATRIX-OS.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\MAGNATRIX-OS.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "QuietUninstallString" "$INSTDIR\uninst.exe /S"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninst.exe"
SectionEnd

Section "Start Menu Shortcuts" SEC02
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\MAGNATRIX-OS.lnk" "$INSTDIR\MAGNATRIX-OS.exe"
    CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\Dashboard.lnk" "http://localhost:8080"
    CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk" "$INSTDIR\uninst.exe"
SectionEnd

Section "Desktop Shortcut" SEC03
    CreateShortcut "$DESKTOP\MAGNATRIX-OS.lnk" "$INSTDIR\MAGNATRIX-OS.exe"
SectionEnd

Section "Run at Startup" SEC04
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "MAGNATRIX-OS" "$INSTDIR\MAGNATRIX-OS.exe"
SectionEnd

; ── Uninstaller ───────────────────────────────────────────────────────────
Section Uninstall
    ; Remove registry
    DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
    DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
    DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "MAGNATRIX-OS"

    ; Remove shortcuts
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\MAGNATRIX-OS.lnk"
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\Dashboard.lnk"
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${PRODUCT_NAME}"
    Delete "$DESKTOP\MAGNATRIX-OS.lnk"

    ; Remove files
    Delete "$INSTDIR\MAGNATRIX-OS.exe"
    Delete "$INSTDIR\python*.dll"
    RMDir /r "$INSTDIR\_internal"
    RMDir /r "$INSTDIR\kernel"
    RMDir /r "$INSTDIR\ai"
    RMDir /r "$INSTDIR\runtime"
    RMDir /r "$INSTDIR\website"
    RMDir /r "$INSTDIR\trading"
    RMDir /r "$INSTDIR\security"
    RMDir /r "$INSTDIR\knowledge"
    RMDir /r "$INSTDIR\p2p_mesh"
    Delete "$INSTDIR\uninst.exe"
    RMDir "$INSTDIR"

    SetAutoClose true
SectionEnd

; ── Descriptions ──────────────────────────────────────────────────────────
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} "Core MAGNATRIX-OS files including kernel, AI modules, and dashboard."
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC02} "Add shortcuts to the Start Menu."
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC03} "Add shortcut to the Desktop."
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC04} "Start MAGNATRIX-OS automatically when Windows boots."
!insertmacro MUI_FUNCTION_DESCRIPTION_END
