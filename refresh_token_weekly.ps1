param(
    [switch]$DryRun,
    [switch]$WriteEnv,
    [string]$ProjectDir = "C:\Users\Moni\MisCosas\Proyectos\github\weather-telegram-bot",
    [string]$ClientSecretsFile = "",
    [string]$EnvFile = ".env",
    [string]$TokenFile = "refresh_tokens.txt",
    [int]$MinimumDaysBetweenRuns = 7
)

$ErrorActionPreference = "Stop"

function Get-LastRefreshTokenRun {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    $newDatePattern = '^(?<date>\d{2}/\d{2}/\d{4} \d{2}:\d{2})h\s+REFRESH_TOKEN:'
    $oldDatePattern = '^(?<date>\d{4}-\d{2}-\d{2}T\S+)'
    $lines = @(Get-Content -LiteralPath $Path)

    for ($index = $lines.Count - 1; $index -ge 0; $index--) {
        $line = $lines[$index]
        if ($line -match $newDatePattern) {
            $parsedDate = [datetime]::MinValue
            if ([datetime]::TryParseExact(
                    $Matches.date,
                    "dd/MM/yyyy HH:mm",
                    [Globalization.CultureInfo]::InvariantCulture,
                    [Globalization.DateTimeStyles]::AssumeLocal,
                    [ref]$parsedDate
                )) {
                return [datetimeoffset]::new($parsedDate)
            }
        }

        if ($line -match $oldDatePattern) {
            $parsedDate = [datetimeoffset]::MinValue
            if ([datetimeoffset]::TryParse($Matches.date, [ref]$parsedDate)) {
                return $parsedDate
            }
        }
    }

    return $null
}

function Get-RefreshTokenFromOutput {
    param([string[]]$OutputLines)

    for ($index = 0; $index -lt $OutputLines.Count; $index++) {
        if ($OutputLines[$index].Trim() -eq "REFRESH TOKEN:") {
            for ($nextIndex = $index + 1; $nextIndex -lt $OutputLines.Count; $nextIndex++) {
                $candidate = $OutputLines[$nextIndex].Trim()
                if ($candidate) {
                    return $candidate
                }
            }
        }
    }

    return $null
}

if (-not (Test-Path -LiteralPath $ProjectDir -PathType Container)) {
    throw "Project directory does not exist: $ProjectDir"
}

Set-Location -LiteralPath $ProjectDir

$tokenFilePath = Join-Path -Path $ProjectDir -ChildPath $TokenFile
$now = [datetimeoffset]::Now
$lastRun = Get-LastRefreshTokenRun -Path $tokenFilePath

if ($lastRun -ne $null) {
    $nextAllowedRun = $lastRun.AddDays($MinimumDaysBetweenRuns)
    if ($now -lt $nextAllowedRun) {
        Write-Host "Last refresh token run: $($lastRun.ToString('o'))"
        Write-Host "Next allowed run: $($nextAllowedRun.ToString('o'))"
        Write-Host "Skipping because fewer than $MinimumDaysBetweenRuns days have passed."
        exit 0
    }
}

if ($DryRun) {
    Write-Host "Dry run: refresh token flow would run now."
    exit 0
}

Write-Host "Installing google-auth-oauthlib if needed..."
$pipCommand = Get-Command pip -ErrorAction SilentlyContinue
if ($pipCommand) {
    & $pipCommand.Source install google-auth-oauthlib
} else {
    & python -m pip install google-auth-oauthlib
}

if ($LASTEXITCODE -ne 0) {
    throw "pip install google-auth-oauthlib failed with exit code $LASTEXITCODE"
}

Write-Host "Running get_refresh_token.py..."
Write-Host "If Google asks you to sign in or approve access, complete that manual step in the browser."
$scriptArgs = @("get_refresh_token.py")
if ($ClientSecretsFile) {
    $scriptArgs += @("--client-secrets", $ClientSecretsFile)
}
if ($WriteEnv) {
    $scriptArgs += @("--write-env", "--env-file", $EnvFile)
}

$scriptOutput = & python @scriptArgs 2>&1
$scriptExitCode = $LASTEXITCODE
$scriptOutput | ForEach-Object { Write-Host $_ }

if ($scriptExitCode -ne 0) {
    throw "python get_refresh_token.py failed with exit code $scriptExitCode"
}

$refreshToken = Get-RefreshTokenFromOutput -OutputLines $scriptOutput
if (-not $refreshToken) {
    throw "get_refresh_token.py did not print a refresh token after 'REFRESH TOKEN:'."
}

$entry = "$($now.ToString('dd/MM/yyyy HH:mm'))h REFRESH_TOKEN:$refreshToken"
Add-Content -LiteralPath $tokenFilePath -Value $entry -Encoding utf8
Write-Host "Saved refresh token entry to $tokenFilePath"
if ($WriteEnv) {
    Write-Host "Updated $EnvFile with GOOGLE_OAUTH_CLIENT_JSON and GOOGLE_OAUTH_REFRESH_TOKEN."
}
