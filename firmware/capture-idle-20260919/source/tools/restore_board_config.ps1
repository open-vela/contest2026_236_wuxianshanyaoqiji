param(
    [string]$Ssid='2F',
    [Security.SecureString]$WifiPassword,
    [Security.SecureString]$ArkKey,
    [Security.SecureString]$AliyunKey
)
$ErrorActionPreference='Stop'
if (-not $WifiPassword) { $WifiPassword=Read-Host 'Wi-Fi password' -AsSecureString }
if (-not $ArkKey) { $ArkKey=Read-Host 'Doubao Ark API key' -AsSecureString }
if (-not $AliyunKey) { $AliyunKey=Read-Host 'Beijing DashScope API key' -AsSecureString }
$wifi=[Net.NetworkCredential]::new('', $WifiPassword).Password
$ark=[Net.NetworkCredential]::new('', $ArkKey).Password
$ali=[Net.NetworkCredential]::new('', $AliyunKey).Password
try {
    foreach ($value in @($Ssid,$wifi,$ark,$ali)) {
        if (-not $value -or $value -match '[\x00-\x1f\x7f''"$`;<>|&\\]') { throw 'Unsupported NSH argument characters' }
    }
    function Send-Board([string]$Command) {
        $start=[Diagnostics.ProcessStartInfo]::new('adb')
        $start.UseShellExecute=$false
        $start.RedirectStandardOutput=$true
        $start.RedirectStandardError=$true
        $start.CreateNoWindow=$true
        $start.ArgumentList.Add('shell'); $start.ArgumentList.Add($Command)
        $process=[Diagnostics.Process]::Start($start)
        try {
            $stdout=$process.StandardOutput.ReadToEndAsync()
            $stderr=$process.StandardError.ReadToEndAsync()
            if (-not $process.WaitForExit(45000)) { $process.Kill(); throw 'ADB timeout; reconnect the board and retry' }
            $output=$stdout.GetAwaiter().GetResult()+$stderr.GetAwaiter().GetResult()
            $output=$output.Replace($wifi,'[PASSWORD]').Replace($ark,'[KEY]').Replace($ali,'[KEY]')
            if ($process.ExitCode -ne 0 -or $output -match 'Unknown command|not ready|command not found|Wi-Fi connection failed') {
                throw ('Device configuration failed: '+$output)
            }
            Write-Host $output.Trim()
        } finally { $process.Dispose() }
    }
    Send-Board "qiji_config wifi '$Ssid' '$wifi'"
    Send-Board "qiji_config set_llm https://ark.cn-beijing.volces.com/api/v3/chat/completions doubao-seed-character-260628 $ark"
    Send-Board "qiji_config set_aliyun_asr $ali"
    $utc=[DateTime]::UtcNow.ToString('MMM dd HH:mm:ss yyyy',[Globalization.CultureInfo]::InvariantCulture)
    Send-Board "date -u -s '$utc'"
    Send-Board 'qiji_config voice_status'
    Send-Board 'ifconfig wlan0'
    Write-Host 'Configuration sent. Check IP, clock and voice_status above; microphone acceptance is separate.'
} finally { $wifi=$ark=$ali=$null }
