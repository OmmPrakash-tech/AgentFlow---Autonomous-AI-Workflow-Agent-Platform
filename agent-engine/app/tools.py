import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid
from .schemas import ToolRequest

EXCLUDED = {".git", ".venv", "node_modules", "target", "dist", "__pycache__", ".idea"}
SENSITIVE = {".env", "id_rsa", "id_ed25519", "credentials", ".npmrc", ".pypirc"}
EXTENSIONS = {".py", ".java", ".ts", ".tsx", ".js", ".json", ".xml", ".properties", ".yml", ".yaml", ".md", ".txt", ".toml", ".gradle", ".sql"}
TOOLS = {"list_files", "read_file", "search_code", "inspect_project", "inspect_dependencies", "security_scan", "inspect_git_diff", "modify_file", "run_tests"}

def redact(text):
    text = re.sub(r"(?im)((?:password|secret|token|api[_-]?key)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", text)
    return re.sub(r"\b(?:ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b", "[REDACTED]", text)

class PolicyError(Exception):
    pass

class Gateway:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def workspace(self, name):
        rel = Path(name)
        if rel.is_absolute() or ":" in name or ".." in rel.parts:
            raise PolicyError("WORKSPACE_ESCAPE")
        result = (self.root / rel).resolve(strict=True)
        if not result.is_relative_to(self.root) or result == self.root or not result.is_dir():
            raise PolicyError("WORKSPACE_ESCAPE")
        return result

    def path(self, workspace, name, file=False):
        rel = Path(name)
        if rel.is_absolute() or ":" in name or ".." in rel.parts:
            raise PolicyError("PATH_TRAVERSAL")
        if any(p in EXCLUDED or p in SENSITIVE or p.startswith(".env.") and p != ".env.example" for p in rel.parts):
            raise PolicyError("SENSITIVE_PATH")
        path = (workspace / rel).resolve(strict=True)
        if not path.is_relative_to(workspace):
            raise PolicyError("WORKSPACE_ESCAPE")
        if file and (not path.is_file() or path.stat().st_size > 100000 or path.suffix.lower() not in EXTENSIONS):
            raise PolicyError("FILE_NOT_ALLOWED")
        # Reject links/junctions even when they currently point inside the workspace.
        cursor = workspace
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink() or (hasattr(cursor, "is_junction") and cursor.is_junction()):
                raise PolicyError("LINK_NOT_ALLOWED")
        return path

    def files(self, workspace):
        result = []
        for parent, dirs, files in os.walk(workspace, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not (Path(parent)/d).is_symlink() and not (hasattr(Path(parent)/d,"is_junction") and (Path(parent)/d).is_junction()))
            for name in sorted(files):
                rel = (Path(parent)/name).relative_to(workspace).as_posix()
                try:
                    self.path(workspace, rel, file=True)
                    result.append(rel)
                except (PolicyError, OSError):
                    continue
                if len(result) >= 500:
                    return result
        return result

    def read(self, workspace, name):
        path = self.path(workspace, name, file=True)
        raw = path.read_bytes()
        return {"path": name, "sha256": hashlib.sha256(raw).hexdigest(),
                "content": redact(raw.decode("utf-8", errors="replace")[:12000])}

    def authorize(self, state, task, request):
        if request.name not in state["tools"] or request.name not in task["tools"]:
            raise PolicyError("TOOL_PERMISSION_DENIED")
        agent = next((a for a in state["agents"] if a["name"] == task["agent"]), None)
        if agent is None or request.name not in agent["configuration"].get("available_tools", []):
            raise PolicyError("AGENT_PERMISSION_DENIED")
        if request.name == "modify_file" and state["mode"] != "EDIT_MODE":
            raise PolicyError("READ_ONLY")
        return self.workspace(state["workspace"])

    def proposal(self, state, task, request):
        workspace = self.authorize(state, task, request)
        if request.name == "modify_file":
            current = self.read(workspace, request.path)
            if current["sha256"] != request.expected_sha256:
                raise PolicyError("STALE_FILE")
            diff = "".join(difflib.unified_diff(current["content"].splitlines(True),
                       request.content.splitlines(True), fromfile=request.path, tofile=request.path))
        else:
            diff = "Execute the fixed Python unittest suite in an isolated, network-disabled container."
        canonical = json.dumps(request.model_dump(), sort_keys=True)
        return {"id": str(uuid.uuid4()), "digest": hashlib.sha256(canonical.encode()).hexdigest(),
                "request": request.model_dump(), "task_id": task["id"], "agent": task["agent"],
                "reason": task["objective"], "risk": "MEDIUM" if request.name == "modify_file" else "HIGH",
                "diff": redact(diff), "created_at": time.time(), "expires_at": time.time()+3600, "decision": "PENDING"}

    def execute(self, state, task, request, approval=None):
        workspace = self.authorize(state, task, request)
        started = time.monotonic()
        if request.name in {"modify_file", "run_tests"}:
            digest = hashlib.sha256(json.dumps(request.model_dump(), sort_keys=True).encode()).hexdigest()
            if not approval or approval["decision"] != "APPROVED" or approval["digest"] != digest or approval["task_id"] != task["id"] or approval["expires_at"] < time.time():
                raise PolicyError("APPROVAL_REQUIRED")
        if request.name in {"list_files", "inspect_project"}:
            value = {"files": self.files(workspace)}
        elif request.name == "read_file":
            value = self.read(workspace, request.path)
        elif request.name in {"search_code", "security_scan", "inspect_dependencies"}:
            rows = []
            for file in self.files(workspace):
                if request.name == "inspect_dependencies" and Path(file).name not in {"pom.xml","package.json","requirements.txt","pyproject.toml","build.gradle"}:
                    continue
                data = self.read(workspace, file)
                for number, line in enumerate(data["content"].splitlines(), 1):
                    match = request.query.lower() in line.lower() if request.name=="search_code" else (request.name=="inspect_dependencies" or re.search(r"(?i)(password|secret|token)\s*[=:]|shell\s*=\s*True|eval\(", line))
                    if match:
                        rows.append({"path": file, "line": number, "text": line[:400]})
                    if len(rows) >= 80:
                        break
                if len(rows) >= 80:
                    break
            value = {"matches": rows, "note": "Heuristic evidence only; not a vulnerability verdict or dependency CVE scan"}
        elif request.name == "inspect_git_diff":
            # Git's external diff and textconv are disabled.
            result = subprocess.run(["git","--no-pager","diff","--no-ext-diff","--no-textconv","--"],cwd=workspace,
                    capture_output=True,timeout=15,env={"PATH":os.environ.get("PATH",""),"SYSTEMROOT":os.environ.get("SYSTEMROOT",""),"GIT_CONFIG_NOSYSTEM":"1","GIT_CONFIG_GLOBAL":os.devnull})
            value = {"exit_code":result.returncode,"diff":redact(result.stdout.decode(errors="replace")[:20000])}
        elif request.name == "modify_file":
            path = self.path(workspace, request.path, file=True)
            before = path.read_bytes()
            if hashlib.sha256(before).hexdigest() != request.expected_sha256:
                raise PolicyError("STALE_FILE")
            # Atomic replace in the same directory; no arbitrary file creation.
            temporary = path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
            try:
                temporary.write_text(request.content, encoding="utf-8", newline="")
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
            value = {"path":request.path,"before_sha256":request.expected_sha256,"after_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"diff":approval["diff"]}
        elif request.name == "run_tests":
            value = self.tests(workspace)
        else:
            raise PolicyError("UNKNOWN_TOOL")
        return {"id":str(uuid.uuid4()),"tool":request.name,"task_id":task["id"],"agent":task["agent"],
                "status":"SUCCEEDED","duration_ms":round((time.monotonic()-started)*1000),"output":value}

    def tests(self, workspace):
        if os.getenv("SANDBOX_ENABLED","false").lower() != "true":
            raise PolicyError("SANDBOX_UNAVAILABLE: test execution requires the configured Docker sandbox")
        name = "agentflow-test-"+uuid.uuid4().hex
        args = ["docker","run","--rm","--name",name,"--network","none","--read-only","--cap-drop","ALL",
                "--security-opt","no-new-privileges","--pids-limit","64","--memory","256m","--cpus","1",
                "--user","65534:65534","--mount",f"type=bind,source={workspace},target=/workspace,readonly",
                "--tmpfs","/tmp:rw,noexec,nosuid,size=32m","-w","/workspace","-e","PYTHONDONTWRITEBYTECODE=1",
                "python:3.14-slim","python","-I","-m","unittest","discover","-s","tests","-v"]
        try:
            r = subprocess.run(args,capture_output=True,timeout=60)
            return {"exit_code":r.returncode,"stdout":redact(r.stdout.decode(errors="replace")[-12000:]),"stderr":redact(r.stderr.decode(errors="replace")[-12000:])}
        except subprocess.TimeoutExpired:
            subprocess.run(["docker","kill",name],capture_output=True,timeout=10)
            raise PolicyError("TOOL_TIMEOUT")
