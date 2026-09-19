param([Security.SecureString]$ApiKey, [string]$PcmFile)
$ErrorActionPreference = 'Stop'
if (-not $ApiKey) { $ApiKey = Read-Host 'Beijing DashScope API Key' -AsSecureString }
$ws = [Net.WebSockets.ClientWebSocket]::new()
$deadline = [Threading.CancellationTokenSource]::new(45000)
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($ApiKey)
try {
    $ws.Options.SetRequestHeader('Authorization', 'Bearer ' + [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr))
} finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
function Send-Frame([byte[]]$Bytes, [Net.WebSockets.WebSocketMessageType]$Type) {
    $null = $ws.SendAsync([ArraySegment[byte]]::new($Bytes), $Type, $true, $deadline.Token).GetAwaiter().GetResult()
}
function Receive-Event {
    $buffer = [byte[]]::new(8192)
    $stream = [IO.MemoryStream]::new()
    try {
        do {
            $r = $ws.ReceiveAsync([ArraySegment[byte]]::new($buffer), $deadline.Token).GetAwaiter().GetResult()
            if ($r.MessageType -eq 'Close') { throw 'Server closed the connection' }
            $stream.Write($buffer, 0, $r.Count)
            if ($stream.Length -gt 65536) { throw 'Oversized server event' }
        } while (-not $r.EndOfMessage)
        $event = [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
        Write-Host ('event: ' + $event.header.event)
        if ($event.header.event -eq 'task-failed') {
            throw ('ASR error: ' + $event.header.error_code + ': ' + $event.header.error_message)
        }
        return $event
    } finally { $stream.Dispose() }
}
try {
    $null = $ws.ConnectAsync([Uri]'wss://dashscope.aliyuncs.com/api-ws/v1/inference', $deadline.Token).GetAwaiter().GetResult()
    $id = [Guid]::NewGuid().ToString()
    $run = @{header=@{action='run-task';task_id=$id;streaming='duplex'};payload=@{
        task_group='audio';task='asr';function='recognition';model='paraformer-realtime-v2';input=@{};
        parameters=@{format='pcm';sample_rate=16000;language_hints=@('zh','en')}
    }} | ConvertTo-Json -Depth 8 -Compress
    Send-Frame ([Text.Encoding]::UTF8.GetBytes($run)) Text
    $event = Receive-Event
    if ($event.header.event -ne 'task-started') { throw 'Missing task-started' }
    $pcm = if ($PcmFile) { [IO.File]::ReadAllBytes((Resolve-Path $PcmFile)) } else { [byte[]]::new(64000) }
    # Short diagnostic recordings only; receive final events immediately after upload.
    if ($pcm.Length -gt 320000 -or $pcm.Length % 2) { throw 'Use <=10 seconds of PCM16 mono 16 kHz' }
    for ($offset = 0; $offset -lt $pcm.Length; $offset += 3200) {
        $len = [Math]::Min(3200, $pcm.Length-$offset)
        $chunk = [byte[]]::new($len)
        [Array]::Copy($pcm,$offset,$chunk,0,$len)
        Send-Frame $chunk Binary
        Start-Sleep -Milliseconds 100
    }
    $finish = @{header=@{action='finish-task';task_id=$id;streaming='duplex'};payload=@{input=@{}}} | ConvertTo-Json -Depth 5 -Compress
    Send-Frame ([Text.Encoding]::UTF8.GetBytes($finish)) Text
    do {
        $event = Receive-Event
        if ($event.payload.output.sentence.sentence_end) { Write-Host ('text: ' + $event.payload.output.sentence.text) }
    } while ($event.header.event -ne 'task-finished')
    Write-Host 'PASS: authenticated task lifecycle completed'
} finally { $ws.Dispose(); $deadline.Dispose() }
