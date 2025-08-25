# sandbox_api/scanners/static_runner.py
import json, os, subprocess, tempfile, time
from typing import Dict, Any, List

def _run(cmd: list[str], cwd: str | None = None, timeout: int = 180) -> tuple[int, str, str]:
    try:
        p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill(); out, err = p.communicate()
        return p.returncode, out, err
    except FileNotFoundError:
        # Tool not found, return empty result
        return 1, "", f"Tool {cmd[0]} not found"

def semgrep_sarif(path: str) -> Dict[str, Any] | None:
    try:
        code, out, err = _run(["semgrep", "--sarif","--quiet","--error","--timeout","120","-r","auto", path])
        return json.loads(out) if out.strip().startswith("{") else None
    except Exception:
        return None

def bandit_sarif(path: str) -> Dict[str, Any] | None:
    try:
        code, out, err = _run(["bandit", "-r", path, "-f", "sarif", "-q"])
        return json.loads(out) if out.strip().startswith("{") else None
    except Exception:
        return None

def pip_audit_sarif(path: str) -> Dict[str, Any] | None:
    try:
        # Check if requirements.txt exists
        req_file = os.path.join(path, "requirements.txt")
        if not os.path.exists(req_file):
            return None
        code, out, err = _run(["pip-audit","-f","sarif","-r","requirements.txt"], cwd=path)
        return json.loads(out) if out.strip().startswith("{") else None
    except Exception:
        return None

def trivy_fs_sarif(path: str) -> Dict[str, Any] | None:
    try:
        code, out, err = _run(["trivy","fs","--format","sarif","--quiet","."] , cwd=path)
        return json.loads(out) if out.strip().startswith("{") else None
    except Exception:
        return None

def gitleaks_sarif(path: str) -> Dict[str, Any] | None:
    try:
        code, out, err = _run(["gitleaks","detect","-s", path, "--no-git","--report-format","sarif"])
        # Check if sarif file was created
        sarif_file = os.path.join(path, "gitleaks.sarif")
        if os.path.exists(sarif_file):
            with open(sarif_file, 'r') as f:
                return json.load(f)
        return None
    except Exception:
        return None

def run_all(path: str) -> List[Dict[str, Any]]:
    res = []
    # Only use tools that are likely to be available
    available_scanners = [semgrep_sarif, bandit_sarif, pip_audit_sarif]
    
    for fn in available_scanners:
        try:
            sarif = fn(path)
            if sarif:
                res.append(sarif)
        except Exception as e:
            print(f"Scanner {fn.__name__} failed: {e}")
            pass
    return res
