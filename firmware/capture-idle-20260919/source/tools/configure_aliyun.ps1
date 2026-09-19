param([Security.SecureString]$ApiKey)
$ErrorActionPreference = 'Stop'
if (-not $ApiKey) { $ApiKey = Read-Host 'Beijing DashScope API Key' -AsSecureString }
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($ApiKey)
try {
    $secret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    if ($secret -notmatch '^sk-[A-Za-z0-9_-]{8,240}$') { throw 'Unexpected key format' }
    $reply = (& adb shell "qiji_config set_aliyun_asr $secret" 2>&1 | Out-String)
    if ($reply -notmatch 'Aliyun ASR configured; key hidden\.') {
        throw 'Configuration not confirmed. Flash the Aliyun firmware and wait for AI Agent ready.'
    }
    Write-Host 'Aliyun ASR configured on device. Key omitted.'
} finally {
    $secret = $null
    $reply = $null
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
