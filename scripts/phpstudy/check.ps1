$ErrorActionPreference = "Stop"

function Test-Endpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    try {
        $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        Write-Host "[OK] $Url -> $($Response.StatusCode)"
    } catch {
        $StatusCode = $null
        $Body = $null
        if ($_.Exception.Response) {
            try {
                $StatusCode = [int]$_.Exception.Response.StatusCode
                $Reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $Body = $Reader.ReadToEnd()
                $Reader.Close()
            } catch {
                $Body = $null
            }
        }

        Write-Host "[FAIL] $Url"
        if ($StatusCode -eq 404 -and $Url -like "http://localhost/*") {
            Write-Host "phpStudy Nginx is reachable, but the localhost vhost is still serving the default site."
            Write-Host "Check that deploy/phpstudy/nginx-agent-panel.conf has been pasted into the active phpStudy site config for localhost, then reload Nginx."
        }
        if ($Body) {
            Write-Host $Body
        }
        throw
    }
}

Test-Endpoint "http://127.0.0.1:8000/health"
Test-Endpoint "http://localhost/health"

Write-Host "phpStudy Nginx proxy and FastAPI service check completed."
