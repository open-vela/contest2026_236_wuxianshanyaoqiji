param(
    [string]$AdbPath,
    [string]$Serial,
    [switch]$KeepWifi,
    [string]$Ssid='2F',
    [Security.SecureString]$WifiPassword,
    [Security.SecureString]$ArkKey,
    [Security.SecureString]$AliyunKey
)
$ErrorActionPreference='Stop'
if (-not $AdbPath) {
    $sdkAdb=Join-Path $env:LOCALAPPDATA 'Android\sdk\platform-tools\adb.exe'
    $AdbPath=if (Test-Path -LiteralPath $sdkAdb) { $sdkAdb } else { (Get-Command adb -ErrorAction Stop).Source }
}
if (-not (Test-Path -LiteralPath $AdbPath)) { throw 'ADB executable not found' }
$devices=& $AdbPath devices 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Cannot list ADB devices' }
$online=@($devices | ForEach-Object { if ("$_" -match '^(\S+)\s+device\s*$') { $Matches[1] } })
if (-not $Serial) {
    if ($online.Count -ne 1) { throw 'Connect exactly one online board, or pass -Serial. Close PhoenixSuit and power-cycle if offline.' }
    $Serial=$online[0]
}
if ($online -notcontains $Serial) { throw 'Selected board is not online' }
if (-not $KeepWifi -and -not $WifiPassword) { $WifiPassword=Read-Host 'Wi-Fi password' -AsSecureString }
if (-not $ArkKey) { $ArkKey=Read-Host 'Doubao Ark API key' -AsSecureString }
if (-not $AliyunKey) { $AliyunKey=Read-Host 'Beijing DashScope API key' -AsSecureString }
$wifi=if ($WifiPassword) { [Net.NetworkCredential]::new('', $WifiPassword).Password } else { '' }
$ark=[Net.NetworkCredential]::new('', $ArkKey).Password
$ali=[Net.NetworkCredential]::new('', $AliyunKey).Password
try {
    $argumentsToCheck=@($ark,$ali)
    if (-not $KeepWifi) { $argumentsToCheck+=@($Ssid,$wifi) }
    foreach ($value in $argumentsToCheck) {
        if (-not $value -or $value -match '[\x00-\x1f\x7f''"$`;<>|&\\]') { throw 'Unsupported NSH argument characters' }
    }
    function Send-Board([string]$Command) {
        $start=[Diagnostics.ProcessStartInfo]::new($AdbPath)
        $start.UseShellExecute=$false
        $start.RedirectStandardOutput=$true
        $start.RedirectStandardError=$true
        $start.CreateNoWindow=$true
        $start.ArgumentList.Add('-s'); $start.ArgumentList.Add($Serial)
        $start.ArgumentList.Add('shell'); $start.ArgumentList.Add($Command)
        $process=[Diagnostics.Process]::Start($start)
        try {
            $stdout=$process.StandardOutput.ReadToEndAsync()
            $stderr=$process.StandardError.ReadToEndAsync()
            if (-not $process.WaitForExit(45000)) { $process.Kill(); throw 'ADB timeout; reconnect the board and retry' }
            $output=$stdout.GetAwaiter().GetResult()+$stderr.GetAwaiter().GetResult()
            if ($wifi) { $output=$output.Replace($wifi,'[PASSWORD]') }
            $output=$output.Replace($ark,'[KEY]').Replace($ali,'[KEY]')
            if ($process.ExitCode -ne 0 -or $output -match 'Unknown command|not ready|command not found|Wi-Fi connection failed|device offline|not found|Usage:') {
                throw ('Device configuration failed: '+$output)
            }
            Write-Host $output.Trim()
        } finally { $process.Dispose() }
    }
    Send-Board "qiji_config set_llm https://ark.cn-beijing.volces.com/api/v3/chat/completions doubao-seed-character-260628 $ark"
    Send-Board "qiji_config set_aliyun_asr $ali"
    Send-Board 'qiji_config set_voice_tts aliyun'
    if (-not $KeepWifi) { Send-Board "qiji_config wifi '$Ssid' '$wifi'" }
    $utc=[DateTime]::UtcNow.ToString('MMM dd HH:mm:ss yyyy',[Globalization.CultureInfo]::InvariantCulture)
    Send-Board "date -u -s '$utc'"
    Send-Board 'qiji_config voice_status'
    Send-Board 'ifconfig wlan0'
    Write-Host 'Configuration sent. Check IP, clock and voice_status above; microphone acceptance is separate. Use -KeepWifi to preserve an already connected network.'
} finally { $wifi=$ark=$ali=$null }
