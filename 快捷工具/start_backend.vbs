' 家庭报销管理系统 - 静默启动后端服务
' 以完全隐藏的方式启动 Flask 后端，无任何弹窗

Dim objShell, objFSO, sScriptDir, sBackendDir, sPythonPath, sScriptPath

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 获取 backend 目录的绝对路径
sScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
sBackendDir = objFSO.GetAbsolutePathName(sScriptDir & "\..\backend")

sPythonPath = "D:\python-file\python.exe"
sScriptPath = sBackendDir & "\app.py"

' 检查文件是否存在
If Not objFSO.FileExists(sPythonPath) Then
    WScript.Quit 1
End If

If Not objFSO.FileExists(sScriptPath) Then
    WScript.Quit 1
End If

' 以隐藏窗口模式启动 Flask（0=隐藏窗口, False=异步执行）
objShell.Run """" & sPythonPath & """ """ & sScriptPath & """", 0, False

Set objShell = Nothing
Set objFSO = Nothing
