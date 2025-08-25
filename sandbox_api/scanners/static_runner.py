# sandbox_api/scanners/static_runner.py
import json, os, subprocess, tempfile, time
from typing import Dict, Any, List

def _run(cmd: list[str], cwd: str | None = None, timeout: int = 180) -> tuple[int, str, str]:
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill(); out, err = p.communicate()
    return p.returncode, out, err

def semgrep_sarif(path: str) -> Dict[str, Any] | None:
    code, out, err = _run(["semgrep", "--sarif","--quiet","--error","--timeout","120","-r","auto", path])
    return json.loads(out) if out.strip().startswith("{") else None

def bandit_sarif(path: str) -> Dict[str, Any] | None:
    code, out, err = _run(["bandit", "-r", path, "-f", "sarif", "-q"])
    return json.loads(out) if out.strip().startswith("{") else None

def pip_audit_sarif(path: str) -> Dict[str, Any] | None:
    code, out, err = _run(["pip-audit","-f","sarif","-r","requirements.txt"], cwd=path)
    return json.loads(out) if out.strip().startswith("{") else None

def trivy_fs_sarif(path: str) -> Dict[str, Any] | None:
    code, out, err = _run(["trivy","fs","--format","sarif","--quiet","."] , cwd=path)
    return json.loads(out) if out.strip().startswith("{") else None

def gitleaks_sarif(path: str) -> Dict[str, Any] | None:
    code, out, err = _run(["gitleaks","detect","-s", path, "--no-git","--report-format","sarif"])
    return json.loads(out) if os.path.exists("gitleaks.sarif") else None

def run_all(path: str) -> List[Dict[str, Any]]:
    res = []
    for fn in [semgrep_sarif, bandit_sarif, pip_audit_sarif, trivy_fs_sarif, gitleaks_sarif]:
        try:
            sarif = fn(path)
            if sarif:
                res.append(sarif)
        except Exception:
            pass
    return res
