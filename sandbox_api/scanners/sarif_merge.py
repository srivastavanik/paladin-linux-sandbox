# sandbox_api/scanners/sarif_merge.py
from typing import List, Dict, Any
import httpx, os

def merge_sarif(sarifs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not sarifs:
        return {"version":"2.1.0","runs":[]}
    base = {"version":"2.1.0","runs":[]}
    for s in sarifs:
        base["runs"].extend(s.get("runs",[]))
    return base

def post_findings(control_plane_url: str, token: str, session_id: str, sarif: Dict[str, Any]) -> None:
    url = f"{control_plane_url.rstrip('/')}/api/findings"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    payload = {"session_id": session_id, "source": "sast", "sarif": sarif}
    httpx.post(url, json=payload, headers=headers, timeout=30)
