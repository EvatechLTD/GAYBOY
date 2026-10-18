$ErrorActionPreference = "Stop"

$ffmpeg  = "ffmpeg.exe"
$ffprobe = "ffprobe.exe"
# LSDj kit preparation: leave headroom below the new Nyquist frequency.
$sampleRate = 11468

Write-Host "===== LSBATCH START ====="
Write-Host "Files received:"
$args | ForEach-Object { Write-Host $_ }

function Reserve-NextOutputFile {
    param(
        [string]$OutDir,
        [string]$Letter
    )

    $mutexName = "LSBATCH_" + ($OutDir.ToUpper().Replace("\","_").Replace(":","")) + "_" + $Letter
    $mutex = New-Object System.Threading.Mutex($false, $mutexName)

    try {
        $null = $mutex.WaitOne()

        $n = 1
        while ($true) {
            $candidate = Join-Path $OutDir ("{0}{1:00}.wav" -f $Letter, $n)

            try {
                $fs = [System.IO.File]::Open(
                    $candidate,
                    [System.IO.FileMode]::CreateNew,
                    [System.IO.FileAccess]::Write,
                    [System.IO.FileShare]::None
                )
                $fs.Close()
                return $candidate
            }
            catch [System.IO.IOException] {
                $n++
            }
        }
    }
    finally {
        $mutex.ReleaseMutex() | Out-Null
        $mutex.Dispose()
    }
}

foreach ($file in $args) {

    Write-Host ""
    Write-Host "Processing: $file"

    $dir = Split-Path $file
    $outDir = Join-Path $dir "processed"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    $name = [System.IO.Path]::GetFileNameWithoutExtension($file)
    $letter = $name.Substring(0,1).ToUpper()

    $outFile = Reserve-NextOutputFile -OutDir $outDir -Letter $letter
    $outName = Split-Path $outFile -Leaf

    $runId = [guid]::NewGuid().ToString()
    $tempFile = Join-Path $env:TEMP "lsbatch_temp_$runId.wav"
    $probeLog = Join-Path $env:TEMP "lsbatch_probe_$runId.txt"
    $volLog   = Join-Path $env:TEMP "lsbatch_vol_$runId.txt"

    try {
        $probeCmd = "$ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=noprint_wrappers=1:nokey=1 `"$file`" > `"$probeLog`" 2>&1"
        cmd.exe /c $probeCmd | Out-Null

        if ($LASTEXITCODE -ne 0) {
            throw "ffprobe failed on $file"
        }

        $channels = (Get-Content $probeLog | Out-String).Trim()

        Write-Host "Channels detected: $channels"

        if ($channels -eq "1") {
            $filter = "highpass=f=20,acompressor=threshold=-22dB:ratio=6:attack=3:release=70,asoftclip,lowpass=f=5000,aresample=${sampleRate}:filter_size=64:cutoff=0.95"
        } else {
            $filter = "pan=mono|c0=0.5*c0+0.5*c1,highpass=f=20,acompressor=threshold=-22dB:ratio=6:attack=3:release=70,asoftclip,lowpass=f=5000,aresample=${sampleRate}:filter_size=64:cutoff=0.95"
        }

        Write-Host "Filter chain:"
        Write-Host $filter
        Write-Host "Output name: $outName"

        $prepCmd = "$ffmpeg -hide_banner -loglevel error -y -i `"$file`" -af `"$filter`" -ar $sampleRate -ac 1 -c:a pcm_s16le `"$tempFile`""
        cmd.exe /c $prepCmd | Out-Null

        if ($LASTEXITCODE -ne 0) {
            throw "ffmpeg preprocess failed on $file"
        }

        if (-not (Test-Path $tempFile)) {
            throw "Temp file not created"
        }

        Write-Host "Detecting peak..."

        $volCmd = "$ffmpeg -hide_banner -nostats -i `"$tempFile`" -af volumedetect -f null NUL > `"$volLog`" 2>&1"
        cmd.exe /c $volCmd | Out-Null

        $volText = Get-Content $volLog | Out-String
        $peakLine = ($volText -split "`r?`n" | Where-Object { $_ -match "max_volume:" } | Select-Object -First 1)

        if (-not $peakLine) {
            Write-Host $volText
            throw "Could not find max_volume in volumedetect output"
        }

        if ($peakLine -match "max_volume:\s*(-?\d+(\.\d+)?)\s*dB") {
            $peak = [double]$matches[1]
        } else {
            throw "Could not parse peak from: $peakLine"
        }

        Write-Host "Peak before normalize: $peak dB"

        $gain = -1 - $peak

        Write-Host "Applying gain: $gain dB"

        $normCmd = "$ffmpeg -hide_banner -loglevel error -y -i `"$tempFile`" -af `"volume=${gain}dB`" -c:a pcm_s16le `"$outFile`""
        cmd.exe /c $normCmd | Out-Null

        if ($LASTEXITCODE -ne 0) {
            throw "ffmpeg normalize failed on $file"
        }

        Write-Host "Finished -> $outFile"
    }
    finally {
        if (Test-Path $tempFile) { Remove-Item $tempFile -Force -ErrorAction SilentlyContinue }
        if (Test-Path $probeLog) { Remove-Item $probeLog -Force -ErrorAction SilentlyContinue }
        if (Test-Path $volLog)   { Remove-Item $volLog -Force -ErrorAction SilentlyContinue }
    }
}

Write-Host ""
Write-Host "===== LSBATCH COMPLETE ====="
