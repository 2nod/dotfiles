import json
from adapter import run
from provider import Provider

for marker in ["SYNTHETIC_ALPHA", "SYNTHETIC_BETA"]:
    url = "https://reference.example.invalid/private/" + marker
    provider = Provider()
    result = run(url, provider)
    assert provider.calls == [url], "Authenticate the server request with the original URL"
    wire = json.dumps(result)
    assert marker not in wire, "Credential-bearing URL reached a client or diagnostic output"
    assert result["session"]["state"] == "ready"
    assert result["history"][0]["type"] == "configuration"
    assert result["stream"][0]["type"] == "update"
    assert result["diagnostics"]["attempt"] == 1
    assert result["other_url"] == "https://public.example.invalid/help"
    assert result["answer"] == "Reference found"
print("All output boundaries are credential-free; server authentication is preserved")
