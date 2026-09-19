param(
    [string]$Ssid = '2F',
    [ValidateSet('character', 'turbo')][string]$Model = 'character',
    [Security.SecureString]$WifiPassword,
    [Security.SecureString]$ApiKey
)
$ErrorActionPreference = 'Stop'
if (-not $WifiPassword) { $WifiPassword = Read-Host 'Wi-Fi password' -AsSecureString }
if (-not $ApiKey) { $ApiKey = Read-Host 'Volcengine Ark API key' -AsSecureString }
$wifi = [Net.NetworkCredential]::new('', $WifiPassword).Password
$key = [Net.NetworkCredential]::new('', $ApiKey).Password
try {
    # NSH supports quoted arguments but does not implement POSIX quote escaping.
    # Reject unsupported shell metacharacters before constructing device commands.
    foreach ($value in @($Ssid, $wifi, $key)) {
        if ($value -match '[\x00-\x1f\x7f''"$`;<>|&\\]') {
            throw 'Input contains a character unsupported by this NSH provisioning tool.'
        }
    }
    if ([Text.Encoding]::UTF8.GetByteCount($Ssid) -gt 32 -or -not $Ssid) { throw 'Invalid SSID length' }
    if ($wifi.Length -lt 8 -or $wifi.Length -gt 63) { throw 'WPA2 password must contain 8 to 63 characters' }
    if (-not $key) { throw 'API key is required' }
    $device = & adb get-state 2>&1
    if ($LASTEXITCODE -ne 0 -or "$device" -notmatch 'device') { throw 'Connect exactly one ADB device' }
    function Invoke-Board([string]$Command) {
        $output = & adb shell $Command 2>&1
        $code = $LASTEXITCODE
        $output | ForEach-Object { "$PSItem".Replace($wifi, '[REDACTED]').Replace($key, '[REDACTED]') }
        if ($code -ne 0) { throw "ADB transport failed ($code)" }
    }
    # This works on the first release too. save_config requires RUNNING, so
    # create the saved network before asking WAPI to associate with it.
    $config = @{wlan0=@{mode=2;auth=4;cmode=8;alg=3;ssid=$Ssid;bssid='';psk=$wifi}} |
        ConvertTo-Json -Depth 4 -Compress
    Invoke-Board "echo '$config' > /data/etc/wifi/wapi.conf"
    Invoke-Board 'wapi disconnect wlan0'
    Invoke-Board 'wapi reconnect wlan0'
    Start-Sleep -Seconds 5
    Invoke-Board 'ifconfig wlan0 0.0.0.0'
    Invoke-Board 'renew wlan0'
    $modelId = if ($Model -eq 'character') { 'doubao-seed-character-260628' } else { 'doubao-seed-2-1-turbo-260628' }
    Invoke-Board "qiji_config set_llm https://ark.cn-beijing.volces.com/api/v3/chat/completions $modelId $key"
    Invoke-Board 'wapi show wlan0'
    Invoke-Board 'qiji_config status'
    Write-Output "Configured $modelId. Verify the screen response; configuration alone is not an inference test."
} finally {
    $wifi = $null
    $key = $null
    $config = $null
}
