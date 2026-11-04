[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Initialize', 'Api', 'Dashboard', 'Verify')]
    [string]$Service
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$tokenPath = Join-Path $projectRoot '.env.monitoring'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'The project virtual environment is missing.'
}

if (-not (Test-Path -LiteralPath $tokenPath)) {
    # Export-Clixml encrypts SecureString using Windows DPAPI for this user/machine.
    # Only encrypted material is written; never put the token in command arguments.
    $randomBytes = New-Object byte[] 32
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($randomBytes)
        $secureToken = ConvertTo-SecureString -String ([Convert]::ToBase64String($randomBytes)) -AsPlainText -Force
        $secureToken | Export-Clixml -LiteralPath $tokenPath -NoClobber
    }
    finally {
        $generator.Dispose()
        [Array]::Clear($randomBytes, 0, $randomBytes.Length)
    }
}

# Restrict the encrypted file to the account running the development services.
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = [System.IO.File]::GetAccessControl(
    $tokenPath, [System.Security.AccessControl.AccessControlSections]::Access
)
$acl.SetAccessRuleProtection($true, $false)
foreach ($existingRule in @($acl.Access)) {
    $acl.RemoveAccessRuleSpecific($existingRule)
}
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $identity, 'FullControl', 'Allow'
)
$acl.AddAccessRule($rule)
[System.IO.File]::SetAccessControl($tokenPath, $acl)

$secureToken = Import-Clixml -LiteralPath $tokenPath
if ($secureToken -isnot [System.Security.SecureString] -or $secureToken.Length -lt 32) {
    throw 'Invalid encrypted monitoring configuration. Do not replace it with plaintext.'
}
if ($Service -eq 'Initialize') {
    Write-Output 'Encrypted local monitoring configuration is ready. Token not displayed.'
    return
}

$previousToken = $env:TRUSTSHIELD_AUDIT_TOKEN
$tokenPointer = [IntPtr]::Zero
Push-Location $projectRoot
try {
    $tokenPointer = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    $env:TRUSTSHIELD_AUDIT_TOKEN = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer)
    $tokenPointer = [IntPtr]::Zero

    switch ($Service) {
        'Api' {
            & $pythonPath -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --no-proxy-headers
        }
        'Dashboard' {
            & $pythonPath -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
        }
        'Verify' {
            @'
import json
import os
import httpx
from streamlit.testing.v1 import AppTest

with httpx.Client(base_url="http://127.0.0.1:8000", trust_env=False, timeout=15) as client:
    anonymous = client.get("/audit")
    wrong = client.get("/audit", headers={"Authorization": "Bearer fictional-invalid-token"})
    authorized = client.get("/audit", headers={
        "Authorization": "Bearer " + os.environ["TRUSTSHIELD_AUDIT_TOKEN"]
    })
    print(json.dumps({"unauthenticated_audit": anonymous.status_code,
                      "incorrect_token_audit": wrong.status_code,
                      "authenticated_audit": authorized.status_code}))
    assert anonymous.status_code == 401
    assert wrong.status_code == 401
    assert authorized.status_code == 200
    snapshot = authorized.json()

app = AppTest.from_file("dashboard.py", default_timeout=30).run()
assert not app.exception, "Dashboard execution failed"
assert not any(w.value == "Persistent security monitoring is unavailable." for w in app.warning)
expected = [str(snapshot["metrics"][key]) for key in ("total", "allowed", "blocked", "held")]
assert [str(metric.value) for metric in app.metric][-4:] == expected
assert len(app.dataframe) == 1
assert len(app.dataframe[0].value) == len(snapshot["records"])
app.button[1].click().run()
assert not app.exception
print(json.dumps({"dashboard_monitoring": "PASS", "persistent_metrics": snapshot["metrics"],
                  "displayed_records": len(app.dataframe[0].value), "refresh": "PASS"}))
'@ | & $pythonPath -
        }
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Local $Service command failed with exit code $LASTEXITCODE."
    }
}
finally {
    if ($tokenPointer -ne [IntPtr]::Zero) {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer)
    }
    $env:TRUSTSHIELD_AUDIT_TOKEN = $previousToken
    Pop-Location
}
