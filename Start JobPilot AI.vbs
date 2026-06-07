' Double-click launcher — opens a console and runs start_jobpilotai.bat
Option Explicit

Dim shell, fso, scriptDir, batPath

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = scriptDir & "\start_jobpilotai.bat"

If Not fso.FileExists(batPath) Then
    MsgBox "Cannot find start_jobpilotai.bat in:" & vbCrLf & scriptDir, vbCritical, "JobPilot AI"
    WScript.Quit 1
End If

' Set working folder first — avoids broken cd quoting on double-click
shell.CurrentDirectory = scriptDir
shell.Run "cmd.exe /c call """ & batPath & """", 1, True
