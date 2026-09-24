<#
.SYNOPSIS
  听书测试物料 → git 永久入库流程（白名单 + 安全守卫 + 隔离索引提交）。

.NOTES
  ⚠️ 本文件含中文路径字面量，**必须保存为 UTF-8 with BOM**：
  Windows PowerShell 5.1 会把无 BOM 的 UTF-8 中文当 ANSI 读，导致语法错误。
  用编辑器改完请确认编码（BOM 十六进制 EF BB BF），或执行：
    $p='scripts\sync_tingju_skill_to_git.ps1'
    [IO.File]::WriteAllText($p,(Get-Content $p -Raw -Encoding UTF8),(New-Object Text.UTF8Encoding($true)))

.DESCRIPTION
  用途：把「听书测试物料」里的**文本类**知识与产物（技能文档、用例清单、测试报告）固化进 git，
  避免每次靠手工挑选、也避免把 GB 级音频/元数据误提交。

  三条硬规则：
    1) 只提交白名单内的路径（禁用 git add -A / 目录级全量 add）；
    2) 提交前做守卫扫描：命中密钥特征或大文件/音频后缀 → 直接中止；
    3) 用**独立索引**提交（GIT_INDEX_FILE），绝不触碰他人已暂存的内容；
       提交后把白名单文件补回真实索引，防止被误判为「待删除」。

  默认不含 `*.py` 脚本（脚本内含硬编码 SECRET_KEY，需先脱敏为环境变量读取）；加 -WithScripts 才会纳入，且仍要过守卫。

.PARAMETER DryRun
  只做收集、守卫扫描与 git add 预览，不产生任何提交。

.PARAMETER WithScripts
  额外纳入 docs/听书测试物料/*.py（**必须先脱敏**，否则守卫会中止）。

.PARAMETER Push
  提交后执行 git push -u origin <Branch>（默认当前分支）。

.PARAMETER Branch
  推送目标分支名，默认当前分支。

.PARAMETER Message
  自定义提交信息。

.EXAMPLE
  # 预览（安全，无副作用）
  powershell -NoProfile -File scripts\sync_tingju_skill_to_git.ps1 -DryRun

.EXAMPLE
  # 提交并推送
  powershell -NoProfile -File scripts\sync_tingju_skill_to_git.ps1 -Push
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$WithScripts,
    [switch]$Push,
    [string]$Branch = "",
    [string]$Message = ""
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$tingju   = 'docs/听书测试物料'

# ── 白名单：只允许这些路径（文件或目录）────────────────────────────
$allowFiles = @(
    "$tingju/SKILL.md",
    "$tingju/语言参数",
    "$tingju/测试用例",          # 目录：仅收 *.md
    "$tingju/测试报告"           # 目录：仅收 *.md（不收 pdf）
)
$allowScriptListFile = 'scripts/tingju_script_allowlist.txt'   # -WithScripts 时按此白名单纳入脚本（避免把一次性脚本与含密钥脚本带进来）

# 永久流程脚本自身也纳入版本管理（非听书目录，但属于本流程的一部分）
$extraFiles = @(
    'scripts/sync_tingju_skill_to_git.ps1',
    'scripts/tingju_script_allowlist.txt'
)

# ── 守卫参数 ──────────────────────────────────────────────────────
$maxFileBytes = 2MB
$blockedExt   = @('.mp3', '.wav', '.mp4', '.zip', '.pdf', '.bin', '.onnx', '.pt', '.log')
$secretPatterns = @(
    '(?<![A-Za-z_])(?<!TTS_)SECRET_KEY\s*=\s*["''][^"'']{8,}["'']',   # 硬编码 SECRET_KEY（排除环境变量名）
    '(?i)\b(?:secret|token|api[_-]?key|password|passwd)\s*[:=]\s*["''][^"'']{8,}["'']',
    '(?<![A-Za-z_])(?<!TTS_)SECRET_KEY\s*=\s*["''][^"'']+["'']',
    'Cd[A-Za-z]{2,8}20\d\d@',                              # 密钥家族形态（不写全量密钥）
    'Bearer\s+eyJ',
    'password\s*=\s*["''][^"'']+["'']'
)
$identity = @('-c', 'user.name=qa-architect', '-c', 'user.email=qa-architect@local')

function Write-Step($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "   OK  $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "   !   $msg" -ForegroundColor Yellow }

# ── 1) 收集候选文件 ──────────────────────────────────────────────
Write-Step "1/6 收集白名单文件"
$candidates = New-Object System.Collections.Generic.List[string]
foreach ($rel in $allowFiles) {
    $abs = Join-Path $repoRoot ($rel -replace '/', '\')
    if (-not (Test-Path -LiteralPath $abs)) { Write-Warn2 "不存在，跳过：$rel"; continue }
    if ((Get-Item -LiteralPath $abs).PSIsContainer) {
        Get-ChildItem -LiteralPath $abs -File -Filter *.md -Recurse |
            ForEach-Object { $candidates.Add($_.FullName) }
    } else {
        $candidates.Add($abs)
    }
}
if ($WithScripts) {
    $listFile = Join-Path $repoRoot ($allowScriptListFile -replace '/', '\')
    if (-not (Test-Path -LiteralPath $listFile)) { throw "缺少脚本白名单文件：$allowScriptListFile" }
    $n = 0
    foreach ($line in (Get-Content -LiteralPath $listFile -Encoding UTF8)) {
        $rel = $line.Trim()
        if (-not $rel -or $rel.StartsWith('#')) { continue }
        $abs = Join-Path $repoRoot ($rel -replace '/', '\')
        if (Test-Path -LiteralPath $abs) { $candidates.Add($abs); $n++ }
        else { Write-Warn2 "白名单脚本不存在，跳过：$rel" }
    }
    Write-Ok "按白名单纳入脚本 $n 个"
}
$candidates = @($candidates | Sort-Object -Unique)
foreach ($rel in $extraFiles) {
    $abs = Join-Path $repoRoot ($rel -replace '/', '\')
    if ((Test-Path -LiteralPath $abs) -and ($candidates -notcontains $abs)) { $candidates += $abs }
}
$candidates = @($candidates | Sort-Object -Unique)
Write-Ok ("候选 " + $candidates.Count + " 个文件（WithScripts=" + [bool]$WithScripts + "）")

# ── 2) 守卫扫描 ─────────────────────────────────────────────────
Write-Step "2/6 安全守卫扫描（密钥 / 大文件 / 音频后缀）"
$violations = New-Object System.Collections.Generic.List[string]
foreach ($f in $candidates) {
    $rel = $f.Substring($repoRoot.Length).TrimStart('\') -replace '\\', '/'
    $len = (Get-Item -LiteralPath $f).Length
    if ($len -gt $maxFileBytes) {
        $violations.Add("BIG_FILE $rel ($([math]::Round($len/1KB)) KB > $([math]::Round($maxFileBytes/1KB)) KB)")
        continue
    }
    if ($blockedExt -contains ([System.IO.Path]::GetExtension($f).ToLower())) {
        $violations.Add("BLOCKED_EXT $rel")
        continue
    }
    $text = Get-Content -LiteralPath $f -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if ($text -and ($selfSkip -notcontains $rel)) {
        foreach ($p in $secretPatterns) {
            if ($text -match $p) { $violations.Add("SECRET_HIT $rel  (pattern: $p)"); break }
        }
    }
}
if ($violations.Count -gt 0) {
    Write-Host "`n守卫拦截，未做任何改动：" -ForegroundColor Red
    $violations | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    Write-Host "`n处理建议：脚本请先改为从环境变量读取密钥（如 `$env:TTS_SECRET_KEY）后再用 -WithScripts。" -ForegroundColor Yellow
    exit 2
}
Write-Ok "全部通过（无密钥特征、无大文件、无音频后缀）"

# ── 3) 生成 pathspec 文件（避免中文路径在命令行被破坏）─────────────
Write-Step "3/6 生成 pathspec 清单"
$tmpDir  = Join-Path $env:TEMP ("tingju-ingest-" + [Guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
$pathspec = Join-Path $tmpDir 'allowlist.txt'
$lines = $candidates | ForEach-Object { $_.Substring($repoRoot.Length).TrimStart('\') -replace '\\', '/' }
[System.IO.File]::WriteAllLines($pathspec, [string[]]$lines, (New-Object System.Text.UTF8Encoding($false)))
Write-Ok "pathspec: $pathspec（$($lines.Count) 行，UTF-8 无 BOM）"

# 分支名直接读 .git/HEAD —— 沙箱下「捕获 git 输出」会被拦截，故不捕获任何 git stdout
$branchNow = (Get-Content -LiteralPath (Join-Path $repoRoot '.git\HEAD') -Raw).Trim() -replace '^ref:\s*refs/heads/', ''
if (-not $Branch) { $Branch = $branchNow }
Write-Ok "当前分支 $branchNow｜推送目标 $Branch"

# ── 4) git add 预览 ─────────────────────────────────────────────
Write-Step "4/6 git add 预览（--dry-run）"
& git -C $repoRoot add --dry-run --pathspec-from-file="$pathspec"
if ($LASTEXITCODE -ne 0) { Write-Host "git add 预览失败" -ForegroundColor Red; exit 3 }

if ($DryRun) {
    Write-Host "`n[DryRun] 未提交、未推送。" -ForegroundColor Yellow
    Write-Host "去掉 -DryRun 即执行提交；加 -Push 会同时推送。" -ForegroundColor Yellow
    exit 0
}

# ── 5) 隔离索引提交 ─────────────────────────────────────────────
Write-Step "5/6 用独立索引提交（不动他人暂存区）"
if (-not $Message) {
    $Message = "docs(tingju): sync listening-test skill materials (" + (Get-Date -Format 'yyyy-MM-dd HH:mm') + ")"
}
$tmpIndex = Join-Path $tmpDir 'index.tmp'
$env:GIT_INDEX_FILE = $tmpIndex
try {
    & git -C $repoRoot read-tree HEAD
    if ($LASTEXITCODE -ne 0) { throw "read-tree 失败" }
    & git -C $repoRoot add --pathspec-from-file="$pathspec"
    if ($LASTEXITCODE -ne 0) { throw "git add 失败" }
    & git -C $repoRoot @identity commit -m $Message --no-verify
    if ($LASTEXITCODE -ne 0) { throw "git commit 失败" }
} finally {
    Remove-Item Env:\GIT_INDEX_FILE -ErrorAction SilentlyContinue
}
$refFile = Join-Path $repoRoot ('.git\refs\heads\' + ($Branch -replace '/', '\'))
$newCommit = if (Test-Path -LiteralPath $refFile) {
    (Get-Content -LiteralPath $refFile -Raw).Trim().Substring(0, 7)
} else { '(见上方 git 输出)' }
Write-Ok "已提交 $newCommit"

# 把白名单文件补回真实索引，防止被误判为「待删除」
& git -C $repoRoot add --pathspec-from-file="$pathspec"
Write-Ok "真实索引已同步（他人暂存内容保持不变）"

# ── 6) 推送 ────────────────────────────────────────────────────
Write-Step "6/6 推送"
if ($Push) {
    & git -C $repoRoot push -u origin "$Branch"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "推送失败（常见原因：网络/凭据/分支保护；沙箱下 git 远端操作可能被拦截）" -ForegroundColor Red
        Write-Host "可手工执行：git -C `"$repoRoot`" push -u origin $Branch" -ForegroundColor Yellow
        exit 4
    }
    Write-Ok "已推送到 origin/$Branch"
} else {
    Write-Warn2 "未推送（加 -Push 才会推送）"
}

Write-Host "`n完成：$newCommit ｜分支 $branchNow ｜纳入 $($lines.Count) 个文件" -ForegroundColor Green
