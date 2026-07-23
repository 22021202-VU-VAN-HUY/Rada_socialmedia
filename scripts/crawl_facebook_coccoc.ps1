[CmdletBinding()]
param(
    [string]$PostUrl,
    [string]$GroupUrl,
    [long]$WindowHandle = 0,
    [int]$GroupScrolls = 10,
    [int]$MaxPosts = 5,
    [switch]$SkipGroup,
    [string]$SourceId = "fb_group_laptrinhvienit",
    [string]$OutputDirectory = "data/exports"
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class CocCocControl
{
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int command);
}
'@

function Get-SampleUrls {
    $path = Join-Path (Get-Location) "textlinkmau.txt"
    if (-not (Test-Path -LiteralPath $path)) {
        return @()
    }

    $content = Get-Content -Raw -LiteralPath $path
    return [regex]::Matches($content, "https://www\.facebook\.com/[^\s]+") |
        ForEach-Object { $_.Value.TrimEnd("#", ",", ".", ")") }
}

function Get-CocCocHandle {
    if ($WindowHandle -ne 0) {
        return [IntPtr]$WindowHandle
    }

    $process = Get-Process browser |
        Where-Object { $_.MainWindowHandle -ne 0 } |
        Select-Object -First 1
    if ($null -eq $process) {
        throw "No visible Coc Coc window was found."
    }
    return $process.MainWindowHandle
}

function Set-CocCocForeground([IntPtr]$Handle) {
    [CocCocControl]::ShowWindow($Handle, 3) | Out-Null
    [CocCocControl]::SetForegroundWindow($Handle) | Out-Null
    Start-Sleep -Milliseconds 350
}

function Open-CocCocUrl([IntPtr]$Handle, [string]$Url) {
    Set-CocCocForeground $Handle
    $quotedUrl = $Url | ConvertTo-Json -Compress
    Set-Clipboard -Value ("script:location.href=" + $quotedUrl + ";void 0")
    [System.Windows.Forms.SendKeys]::SendWait("^l")
    [System.Windows.Forms.SendKeys]::SendWait("java")
    [System.Windows.Forms.SendKeys]::SendWait("^v")
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Start-Sleep -Seconds 7
}

function Open-CocCocUrlDirect([IntPtr]$Handle, [string]$Url) {
    Set-CocCocForeground $Handle
    Set-Clipboard -Value $Url
    [System.Windows.Forms.SendKeys]::SendWait("^l")
    [System.Windows.Forms.SendKeys]::SendWait("^v")
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Start-Sleep -Seconds 7
}

function Get-CanonicalFacebookUrl([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url) -or $Url -match "\shttps?://") {
        throw "Expected one Facebook URL, received a combined or empty value."
    }
    $uri = [Uri]$Url
    $path = $uri.GetLeftPart([UriPartial]::Path).TrimEnd("/") + "/"
    return $path
}

function Invoke-CocCocJavascript(
    [IntPtr]$Handle,
    [string]$Javascript,
    [int]$WaitSeconds = 2
) {
    Set-CocCocForeground $Handle
    Set-Clipboard -Value ("script:" + $Javascript)
    [System.Windows.Forms.SendKeys]::SendWait("^l")
    # Chromium strips a pasted javascript: prefix. Type "java" and paste the rest.
    [System.Windows.Forms.SendKeys]::SendWait("java")
    [System.Windows.Forms.SendKeys]::SendWait("^v")
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Start-Sleep -Seconds $WaitSeconds
}

function Expand-FacebookReplies([IntPtr]$Handle) {
    $script = @"
(()=>{const m=[...document.querySelectorAll('[role=button]')].filter(e=>/^Xem \d+ ph\u1ea3n h\u1ed3i$/.test((e.innerText||'').trim()));const x=m.filter(e=>!m.some(o=>o!==e&&e.contains(o)));x.forEach(e=>e.click());document.title='EXPANDED_'+x.length;void 0})()
"@
    for ($round = 0; $round -lt 4; $round++) {
        Invoke-CocCocJavascript $Handle $script 3
    }
}

function Select-FacebookAllComments([IntPtr]$Handle) {
    $openScript = @"
(()=>{const label='Ph\u00f9 h\u1ee3p nh\u1ea5t';const m=[...document.querySelectorAll('[role=button]')].filter(e=>(e.innerText||'').trim()===label);const x=m.filter(e=>!m.some(o=>o!==e&&e.contains(o)))[0];if(x)x.click();document.title='COMMENT_SORT_OPEN_'+(x?1:0);void 0})()
"@
    Invoke-CocCocJavascript $Handle $openScript 1

    $selectScript = @"
(()=>{const label='T\u1ea5t c\u1ea3 b\u00ecnh lu\u1eadn';const m=[...document.querySelectorAll('[role=menuitem],[role=button]')].filter(e=>(e.innerText||'').trim().startsWith(label));const x=m.filter(e=>!m.some(o=>o!==e&&e.contains(o)))[0];if(x)x.click();document.title='COMMENT_SORT_ALL_'+(x?1:0);void 0})()
"@
    Invoke-CocCocJavascript $Handle $selectScript 4
}

function Copy-FacebookPostJson([IntPtr]$Handle) {
    $script = @"
(()=>{const ds=[...document.querySelectorAll('[role=dialog]')];const reply='Tr\u1ea3 l\u1eddi',share='Chia s\u1ebb';const d=ds.filter(x=>x.querySelector('[data-ad-rendering-role=story_message]')).sort((a,b)=>(b.innerText||'').length-(a.innerText||'').length)[0];if(!d){document.title='POST_DIALOG_NOT_FOUND';return;}const clean=x=>(x||'').replace(/\u00a0/g,' ').trim();const comments=[...d.querySelectorAll('[role=article]')].map((e,i)=>{const lines=(e.innerText||'').split('\n').map(clean).filter(x=>x&&x!=='\u00b7'&&x!==reply&&x!==share);const aria=e.getAttribute('aria-label')||'';const raw=[...e.querySelectorAll('a[href]')].map(a=>a.href).find(h=>h.includes('comment_id='))||null;let permalink=null,externalId=null,parentExternalId=null;if(raw){const u=new URL(raw);const commentId=u.searchParams.get('comment_id');const replyId=u.searchParams.get('reply_comment_id');externalId=replyId||commentId;parentExternalId=replyId?commentId:null;permalink=u.origin+u.pathname+'?comment_id='+commentId+(replyId?'&reply_comment_id='+replyId:'');}const match=aria.match(/^Ph\u1ea3n h\u1ed3i b\u00ecnh lu\u1eadn c\u1ee7a (.+) d\u01b0\u1edbi t\u00ean /)||aria.match(/\u0111\u00e1p l\u1ea1i ph\u1ea3n h\u1ed3i c\u1ee7a (.+) v\u00e0o /);return{index:i+1,external_id:externalId,parent_external_id:parentExternalId,author:lines[0]||null,published_label:lines[1]||null,content:lines.slice(2).join('\n'),is_reply:!!parentExternalId,parent_author:match?match[1]:null,permalink,aria_label:aria};});const message=d.querySelector('[data-ad-rendering-role=story_message]')?.innerText||'';const title=(d.innerText||'').split('\n')[0]||'';const nums=[...d.querySelectorAll('[role=button]')].map(e=>clean(e.innerText)).filter(x=>/^\d+$/.test(x));const post={url:location.href.split('?')[0],external_id:(location.href.match(/\/(?:permalink|posts)\/(\d+)/)||[])[1]||null,author:title.replace(/^B\u00e0i vi\u1ebft c\u1ee7a /,''),group:d.querySelector('[data-ad-rendering-role=profile_name]')?.innerText||null,content:message,reaction_count:Number(nums[0]||0),reported_comment_count:Number(nums[1]||comments.length),collected_comment_count:comments.length};const payload=JSON.stringify({post,comments},null,2);const t=document.createElement('textarea');t.value=payload;document.body.appendChild(t);t.select();document.execCommand('copy');t.remove();document.title='COPIED_POST_'+comments.length;void 0})()
"@
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        Invoke-CocCocJavascript $Handle $script 2
        $clipboard = Get-Clipboard -Raw
        try {
            return $clipboard | ConvertFrom-Json
        }
        catch {
            Start-Sleep -Seconds 4
        }
    }
    throw "Facebook post extraction did not return JSON. Active tab title may identify the blocked page."
}

function Get-FacebookGroupPostUrls([IntPtr]$Handle, [string]$Url) {
    Open-CocCocUrlDirect $Handle $Url
    $scrollScript = @"
(()=>{window.__talentRadarPostLinks=new Set();const collect=()=>{for(const a of document.querySelectorAll('a[href]')){const h=a.href.split('?')[0];if(/\/groups\/[^/]+\/(posts|permalink)\/\d+\/?$/.test(h))window.__talentRadarPostLinks.add(h);}};let n=0;collect();const timer=setInterval(()=>{for(const e of document.querySelectorAll('[role=article] [role=button]')){if((e.innerText||'').trim()==='Xem th\u00eam')e.click();}collect();window.scrollTo(0,document.body.scrollHeight);n++;document.title='GROUP_SCROLL_'+n;if(n>=$GroupScrolls){clearInterval(timer);collect();document.title='GROUP_LOADED_'+n;}},900);void 0})()
"@
    Invoke-CocCocJavascript $Handle $scrollScript ($GroupScrolls + 3)

    $copyScript = @"
(()=>{const current=[...document.querySelectorAll('a[href]')].map(a=>a.href.split('?')[0]).filter(h=>/\/groups\/[^/]+\/(posts|permalink)\/\d+\/?$/.test(h));const links=[...new Set([...(window.__talentRadarPostLinks||[]),...current])];const t=document.createElement('textarea');t.value=JSON.stringify(links);document.body.appendChild(t);t.select();document.execCommand('copy');t.remove();document.title='GROUP_LINKS_'+links.length;void 0})()
"@
    Invoke-CocCocJavascript $Handle $copyScript 2
    $decodedLinks = Get-Clipboard -Raw | ConvertFrom-Json
    $decodedLinks | Select-Object -First $MaxPosts | ForEach-Object {
        Write-Output ([string]$_)
    }
}

$sampleUrls = @(Get-SampleUrls)
if (-not $PostUrl) {
    $PostUrl = $sampleUrls | Where-Object { $_ -match "/(permalink|posts)/" } | Select-Object -First 1
}
if (-not $GroupUrl -and -not $SkipGroup) {
    $GroupUrl = $sampleUrls |
        Where-Object { $_ -match "/groups/[^/]+/?$" } |
        Select-Object -First 1
}
if (-not $PostUrl -and -not $GroupUrl) {
    throw "Provide -PostUrl or -GroupUrl, or add Facebook URLs to textlinkmau.txt."
}

$handle = Get-CocCocHandle
$postUrls = New-Object System.Collections.Generic.List[string]
if ($PostUrl) {
    $postUrls.Add((Get-CanonicalFacebookUrl $PostUrl))
}
if ($GroupUrl -and -not $SkipGroup) {
    foreach ($url in Get-FacebookGroupPostUrls $handle $GroupUrl) {
        $canonicalUrl = Get-CanonicalFacebookUrl $url
        if (-not $postUrls.Contains($canonicalUrl)) {
            $postUrls.Add($canonicalUrl)
        }
    }
}

$results = New-Object System.Collections.Generic.List[object]
$failures = New-Object System.Collections.Generic.List[object]
foreach ($url in $postUrls) {
    try {
        Open-CocCocUrl $handle $url
        Select-FacebookAllComments $handle
        Expand-FacebookReplies $handle
        $item = Copy-FacebookPostJson $handle
        $item | Add-Member -NotePropertyName collected_at -NotePropertyValue (
            [DateTimeOffset]::Now.ToString("o")
        )
        $results.Add($item)
    }
    catch {
        $title = (Get-Process browser |
            Where-Object { $_.MainWindowHandle -eq $handle.ToInt64() }).MainWindowTitle
        $failures.Add(
            [pscustomobject]@{
                url = $url
                error = $_.Exception.Message
                tab_title = $title
            }
        )
    }
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$jsonPath = Join-Path $OutputDirectory "facebook_coccoc_$stamp.json"
$csvPath = Join-Path $OutputDirectory "facebook_coccoc_$stamp.csv"

$payload = [ordered]@{
    crawler = "coccoc-ui"
    collected_at = [DateTimeOffset]::Now.ToString("o")
    source_id = $SourceId
    source_group_url = $GroupUrl
    source_post_url = $PostUrl
    posts = $results
    failures = $failures
}
$payload | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 -LiteralPath $jsonPath

$rows = foreach ($item in $results) {
    [pscustomobject]@{
        item_type = "post"
        source_id = $SourceId
        external_id = $item.post.external_id
        parent_external_id = $null
        author = $item.post.author
        published_label = $null
        content = $item.post.content
        permalink = $item.post.url
        source_post_url = $item.post.url
    }
    foreach ($comment in $item.comments) {
        [pscustomobject]@{
            item_type = "comment"
            source_id = $SourceId
            external_id = $comment.external_id
            parent_external_id = $comment.parent_external_id
            author = $comment.author
            published_label = $comment.published_label
            content = $comment.content
            permalink = $comment.permalink
            source_post_url = $item.post.url
        }
    }
}
$rows | Export-Csv -NoTypeInformation -Encoding utf8 -LiteralPath $csvPath

Write-Output ([pscustomobject]@{
    window_handle = $handle.ToInt64()
    post_count = $results.Count
    item_count = @($rows).Count
    failed_post_count = $failures.Count
    json_path = (Resolve-Path $jsonPath).Path
    csv_path = (Resolve-Path $csvPath).Path
})
