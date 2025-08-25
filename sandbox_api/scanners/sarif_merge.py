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
    try:
        url = f"{control_plane_url.rstrip('/')}/api/findings"
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        payload = {"session_id": session_id, "source": "sast", "sarif": sarif}
        
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
    except Exception as e:
        # Log error but don't fail the scan
        print(f"Failed to post findings to control plane: {e}")
