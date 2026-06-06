# =============================================================================
#  Soly Terminal Bootstrap
#  Replicates the flame-S / fastfetch / oh-my-posh setup on any Windows 10/11 PC.
#  Usage:  iex (gc .\setup-terminal.ps1 -Raw)   or just:   .\setup-terminal.ps1
#  Idempotent — safe to re-run. Requires Internet. Will prompt for UAC.
# =============================================================================
[CmdletBinding()]
param(
    [switch]$SkipFonts,
    [switch]$SkipPackages
)

$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"

function Write-Step ($msg) { Write-Host "==> " -ForegroundColor Cyan -NoNewline; Write-Host $msg }
function Write-Ok   ($msg) { Write-Host "    OK   " -ForegroundColor Green -NoNewline; Write-Host $msg }
function Write-Skip ($msg) { Write-Host "    SKIP " -ForegroundColor DarkGray -NoNewline; Write-Host $msg }
function Write-Warn2($msg) { Write-Host "    WARN " -ForegroundColor Yellow -NoNewline; Write-Host $msg }

# ---------- 1) self-elevate (only if we'll touch system fonts) -------------
$current = [System.Security.Principal.WindowsPrincipal][System.Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = $current.IsInRole([System.Security.Principal.WindowsBuiltinRole]::Administrator)
$needAdmin = -not $SkipFonts
if ($needAdmin -and -not $isAdmin) {
    Write-Step "Re-launching as Administrator (needed for system-wide font install)..."
    $relaunchArgs = @("-NoProfile","-ExecutionPolicy","Bypass","-File","`"$PSCommandPath`"")
    if ($SkipFonts)    { $relaunchArgs += "-SkipFonts" }
    if ($SkipPackages) { $relaunchArgs += "-SkipPackages" }
    Start-Process powershell.exe -Verb RunAs -ArgumentList $relaunchArgs -Wait
    exit
}
if (-not $isAdmin) { Write-Skip "Running as normal user (fonts skipped — pass without -SkipFonts to install them)" }

# ---------- 2) detect Windows version --------------------------------------
$build  = [int](Get-CimInstance Win32_OperatingSystem).BuildNumber
$isWin11 = $build -ge 22000
$winVer  = if ($isWin11) { "Windows 11 (build $build)" } else { "Windows 10 (build $build)" }
Write-Step "Detected: $winVer"
if ($build -lt 17763) {
    Write-Warn2 "Build < 17763 — some features (Windows Terminal, fastfetch glyphs) may not work."
}

# ---------- 3) winget present? ---------------------------------------------
$winget = (Get-Command winget -ErrorAction SilentlyContinue).Source
if (-not $winget) {
    Write-Warn2 "winget not found. On Win10 install 'App Installer' from Microsoft Store first, then re-run."
    Write-Warn2 "Opening Store page..."
    Start-Process "ms-windows-store://pdp/?ProductId=9NBLGGH4NNS1"
    return
}
Write-Ok "winget OK ($winget)"

# ---------- 4) install packages -------------------------------------------
function Install-WingetPackage($id, $pretty) {
    $hit = winget list --id $id -e --accept-source-agreements 2>$null | Select-String -Pattern $id -SimpleMatch
    if ($hit) { Write-Skip "$pretty already installed"; return }
    Write-Step "Installing $pretty ($id)..."
    winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements --scope user 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Ok "$pretty installed" } else { Write-Warn2 "$pretty install returned exit $LASTEXITCODE" }
}

if (-not $SkipPackages) {
    Install-WingetPackage "JanDeDobbeleer.OhMyPosh" "Oh My Posh"
    Install-WingetPackage "Fastfetch-cli.Fastfetch" "fastfetch"
    # Windows Terminal: ship by default on Win11, often missing on Win10
    if (-not $isWin11) { Install-WingetPackage "Microsoft.WindowsTerminal" "Windows Terminal" }
} else { Write-Skip "Package install skipped (--SkipPackages)" }

# refresh PATH so newly-installed exes are findable in this session
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path","User")

# ---------- 5) install JetBrainsMono Nerd Font system-wide -----------------
function Install-NerdFont {
    $needed = "JetBrainsMonoNerdFontMono-Regular.ttf"
    $marker = Join-Path "$env:windir\Fonts" $needed
    if (Test-Path $marker) { Write-Skip "JetBrainsMono Nerd Font already in $env:windir\Fonts"; return }

    Write-Step "Downloading JetBrainsMono Nerd Font..."
    $tmpZip = Join-Path $env:TEMP "JetBrainsMono-NF.zip"
    $tmpDir = Join-Path $env:TEMP "JetBrainsMono-NF"
    $url    = "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip"
    try {
        Invoke-WebRequest -Uri $url -OutFile $tmpZip -UseBasicParsing
    } catch {
        Write-Warn2 "Download failed: $($_.Exception.Message)"
        return
    }
    if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force }
    Expand-Archive -Path $tmpZip -DestinationPath $tmpDir -Force

    $reg = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
    $count = 0
    foreach ($f in Get-ChildItem $tmpDir -Recurse -Include *.ttf,*.otf) {
        # only Mono variants (which carry the 'Nerd Font Mono' typographic name)
        if ($f.Name -notmatch "Mono\.ttf$|NerdFontMono") {
            # still install the regular set too for flexibility
        }
        $dest = Join-Path "$env:windir\Fonts" $f.Name
        Copy-Item $f.FullName $dest -Force
        New-ItemProperty -Path $reg -Name "$($f.BaseName) (TrueType)" -Value $f.Name -PropertyType String -Force | Out-Null
        $count++
    }
    Remove-Item $tmpZip,$tmpDir -Recurse -Force -ErrorAction SilentlyContinue

    # broadcast WM_FONTCHANGE so running apps pick it up
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public class FB { [DllImport("user32.dll")] public static extern IntPtr SendMessageTimeout(IntPtr h, uint m, IntPtr w, IntPtr l, uint f, uint t, out IntPtr r); }
'@ -ErrorAction SilentlyContinue
    $r = [IntPtr]::Zero
    [FB]::SendMessageTimeout([IntPtr]0xffff, 0x001D, [IntPtr]::Zero, [IntPtr]::Zero, 0, 1000, [ref]$r) | Out-Null
    Write-Ok "Installed $count font files"
}
if (-not $SkipFonts) { Install-NerdFont } else { Write-Skip "Font install skipped (--SkipFonts)" }

# ---------- 6) write config files (embedded) ------------------------------
function Save-Config($path, $content) {
    $dir = Split-Path $path
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    if (Test-Path $path) { Copy-Item $path "$path.bak" -Force }
    [System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))
}

# ---- 6a) flame-S ASCII logo ---------------------------------------------
$ASCII_LOGO = @'
$1                  +
$1                  *: .=
$1                  =%+*█+
$2           :-=+==-.:+#@█+-=
$2       .+%@████████@*: -#██%.::
$2      +@███@#*++*%████%: -@█*.*
$3     %███#: -++=-..*@██@- :████:
$3    #███* =@█#      :@██@. *███%
$3   .████ .███%.      +███= :███@
$4    ████  %███@+:    -███@+%███+
$4    *███#. +@████@*-  -@█████@*
$4     +███@#-.:=++++++:  :===-
$5      .*@████@%%%%%%%%%%=
$5    .:.   :-------:-+@███@=
$6 :#@███@#: :+%████@#- :%███*
$6-@██@%@███-   .=#████#  @███.
$6%███= -███*      :%███- %███:
$7%███* .@██@.      =██# :███@
$7:████: =███@- .-=*%*- =@██@-
$7 %-#█@: -@███@*=---=*@███%:
$8 ::.%██*. =%███████████#=
$8     *+#█#+-.-+*##**+-.
$8        +█@#@=
$9         +: :%
$9             *
'@

# ---- 6b) fastfetch config (Nerd Font glyphs built at runtime to avoid encoding issues)
$asciiPath = "$env:USERPROFILE\.config\fastfetch\ascii.txt"
$asciiPathJson = $asciiPath -replace '\\','/'
$ICO_OS     = [char]::ConvertFromUtf32(0xF17A)   # Windows logo
$ICO_CPU    = [char]::ConvertFromUtf32(0xF4BC)   # CPU chip
$ICO_BOARD  = [char]::ConvertFromUtf32(0xF0697)  # motherboard
$ICO_MEM    = [char]::ConvertFromUtf32(0xF0C9)   # bars (memory)
$ICO_DISK   = [char]::ConvertFromUtf32(0xF0A0)   # hard disk
$FASTFETCH_CONFIG = @"
{
  "`$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
  "logo": {
    "type": "file",
    "source": "$asciiPathJson",
    "color": {
      "1": "#7DF0E0",
      "2": "#5FE9DA",
      "3": "#43E0D2",
      "4": "#39D0C8",
      "5": "#35C4D0",
      "6": "#34B5DA",
      "7": "#3AA5E2",
      "8": "#4F92E8",
      "9": "#6680EE"
    },
    "padding": { "top": 1, "right": 3 }
  },
  "display": { "separator": " " },
  "modules": [
    "break",
    { "type": "title", "color": { "user": "#7DF0E0", "at": "#585B70", "host": "#6680EE" } },
    "break",
    { "type": "os",     "key": "$ICO_OS",    "keyColor": "#5FE9DA" },
    { "type": "cpu",    "key": "$ICO_CPU",   "keyColor": "#43E0D2" },
    { "type": "board",  "key": "$ICO_BOARD", "keyColor": "#39D0C8" },
    { "type": "memory", "key": "$ICO_MEM",   "keyColor": "#35C4D0", "format": "{used} / {total} ({percentage})" },
    { "type": "disk",   "key": "$ICO_DISK",  "keyColor": "#3AA5E2" },
    "break",
    { "type": "colors", "symbol": "circle" }
  ]
}
"@

# ---- 6c) oh-my-posh theme -----------------------------------------------
$OMP_THEME = @'
{
  "$schema": "https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.json",
  "version": 3,
  "final_space": true,
  "blocks": [
    {
      "type": "prompt",
      "alignment": "left",
      "segments": [
        {
          "type": "os",
          "style": "diamond",
          "leading_diamond": "",
          "trailing_diamond": "",
          "foreground": "#0D1117",
          "background": "#7DF0E0",
          "template": " {{ .Icon }} "
        },
        {
          "type": "path",
          "style": "powerline",
          "powerline_symbol": "",
          "foreground": "#0D1117",
          "background": "#39D0C8",
          "properties": {
            "style": "agnoster_short",
            "max_depth": 3,
            "folder_icon": "",
            "home_icon": " ",
            "folder_separator_icon": "  "
          },
          "template": " {{ .Path }} "
        },
        {
          "type": "git",
          "style": "powerline",
          "powerline_symbol": "",
          "foreground": "#0D1117",
          "background": "#5FE9DA",
          "background_templates": [
            "{{ if or (.Working.Changed) (.Staging.Changed) }}#F5C97B{{ end }}",
            "{{ if and (gt .Ahead 0) (gt .Behind 0) }}#F38BA8{{ end }}",
            "{{ if gt .Behind 0 }}#B4A0F0{{ end }}"
          ],
          "properties": {
            "branch_icon": " ",
            "fetch_status": true,
            "fetch_upstream_icon": true
          },
          "template": " {{ .UpstreamIcon }}{{ .HEAD }}{{ if .Working.Changed }}  {{ .Working.String }}{{ end }}{{ if .Staging.Changed }}  {{ .Staging.String }}{{ end }} "
        }
      ]
    },
    {
      "type": "rprompt",
      "segments": [
        {
          "type": "executiontime",
          "style": "plain",
          "foreground": "#6C7086",
          "properties": { "threshold": 500, "style": "austin" },
          "template": " {{ .FormattedMs }}"
        }
      ]
    },
    {
      "type": "prompt",
      "alignment": "left",
      "newline": true,
      "segments": [
        {
          "type": "text",
          "style": "plain",
          "foreground": "#7DF0E0",
          "foreground_templates": [ "{{ if gt .Code 0 }}#F38BA8{{ end }}" ],
          "template": "❯"
        }
      ]
    }
  ]
}
'@

Write-Step "Writing config files..."
Save-Config "$env:USERPROFILE\.config\fastfetch\ascii.txt"           $ASCII_LOGO
Save-Config "$env:USERPROFILE\.config\fastfetch\config.jsonc"        $FASTFETCH_CONFIG
Save-Config "$env:USERPROFILE\.config\ohmyposh\soly.omp.json"        $OMP_THEME
Write-Ok "fastfetch config + flame-S logo + oh-my-posh theme written"

# ---------- 7) PowerShell profile (5.1 + 7) ------------------------------
$profileSnippet = @'

# --- Soly terminal -----------------------------------------------------------
oh-my-posh init pwsh --config "$env:USERPROFILE\.config\ohmyposh\soly.omp.json" | Invoke-Expression
if (Get-Command fastfetch -ErrorAction SilentlyContinue) { fastfetch }
# -----------------------------------------------------------------------------
'@

function Ensure-Profile($path) {
    $dir = Split-Path $path
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    if (-not (Test-Path $path)) { New-Item -ItemType File -Path $path | Out-Null }
    $existing = Get-Content $path -Raw -ErrorAction SilentlyContinue
    if ($existing -match "Soly terminal") { Write-Skip "profile $path already configured"; return }
    Add-Content -Path $path -Value $profileSnippet -Encoding utf8
    Write-Ok "patched profile: $path"
}
Write-Step "Patching PowerShell profiles..."
Ensure-Profile "$env:USERPROFILE\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
Ensure-Profile "$env:USERPROFILE\Documents\PowerShell\Microsoft.PowerShell_profile.ps1"

# ---------- 8) Windows Terminal font face --------------------------------
$wtSettings = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"
if (Test-Path $wtSettings) {
    Write-Step "Updating Windows Terminal font face..."
    try {
        Copy-Item $wtSettings "$wtSettings.bak" -Force
        $raw = Get-Content $wtSettings -Raw
        $json = $raw | ConvertFrom-Json
        if (-not $json.profiles) { $json | Add-Member -NotePropertyName profiles -NotePropertyValue ([pscustomobject]@{}) -Force }
        if (-not $json.profiles.defaults) {
            $json.profiles | Add-Member -NotePropertyName defaults -NotePropertyValue ([pscustomobject]@{}) -Force
        }
        $font = [pscustomobject]@{ face = "JetBrainsMono Nerd Font Mono" }
        $json.profiles.defaults | Add-Member -NotePropertyName font -NotePropertyValue $font -Force
        ($json | ConvertTo-Json -Depth 20) | Set-Content $wtSettings -Encoding utf8
        Write-Ok "Windows Terminal default font set to JetBrainsMono Nerd Font Mono"
    } catch {
        Write-Warn2 "Could not patch Windows Terminal settings: $($_.Exception.Message)"
    }
} else {
    Write-Skip "Windows Terminal settings.json not found — open Terminal once, then re-run for font patch"
}

# ---------- 9) done ------------------------------------------------------
Write-Host ""
Write-Host "==> All done!" -ForegroundColor Green
Write-Host "    Open a fresh Windows Terminal window to see the new prompt + fastfetch banner."
Write-Host ""
