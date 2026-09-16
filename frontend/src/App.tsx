import { useState, useEffect, type FormEvent, type ReactNode } from "react";
import {
  NavLink,
  Routes,
  Route,
  Link,
  useParams,
  useNavigate,
} from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  Box,
  Check,
  ChevronRight,
  Command,
  FileText,
  GitBranch,
  Layers,
  Lock,
  Play,
  Plus,
  Shield,
  Terminal,
  Users,
  Workflow,
  X,
  Zap,
} from "lucide-react";
import { api, setToken, stateStream, exportReport, type User } from "./api";

const nav = [
  ["Dashboard", "/", Layers],
  ["Projects", "/projects", Box],
  ["Workflows", "/workflows", Workflow],
  ["Agents", "/agents", Users],
  ["Tools", "/tools", Terminal],
  ["Agent Runs", "/runs", Activity],
  ["Approvals", "/approvals", Shield],
  ["Activity", "/activity", FileText],
  ["Security", "/security", Lock],
] as const;
const terminal = new Set(["COMPLETED", "FAILED", "CANCELLED"]);
function Badge({ value }: { value: string }) {
  return (
    <span className={"badge " + value.toLowerCase()}>
      <i />
      {value.replaceAll("_", " ")}
    </span>
  );
}
function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <Workflow size={32} />
      <h3>{title}</h3>
      <p>
        {children ||
          "Your workspace is ready. Create a project and launch your first objective."}
      </p>
    </div>
  );
}
function ErrorBox({ error }: { error: unknown }) {
  return error ? (
    <div role="alert" className="error">
      {error instanceof Error ? error.message : String(error)}
    </div>
  ) : null;
}
function Heading({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow: string;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{children}</p>
      </div>
      {action}
    </header>
  );
}
function useList(path: string) {
  return useQuery({
    queryKey: [path],
    queryFn: () => api(path),
    refetchInterval:
      path.startsWith("/runs") || path.startsWith("/approvals") ? 5000 : false,
  });
}

function Auth({ onLogin }: { onLogin: (u: User) => void }) {
  const [mode, setMode] = useState("login"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      const data = await api("/auth/" + mode, {
        email: f.get("email"),
        password: f.get("password"),
      });
      setToken(data.accessToken);
      onLogin(data.user);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth">
      <section className="auth-story">
        <div className="brand">
          <span>
            <Workflow />
          </span>
          AgentFlow<span className="version">WORKSPACE</span>
        </div>
        <div>
          <div className="eyebrow">AUTONOMOUS, WITH ACCOUNTABILITY</div>
          <h1>
            From objective.
            <br />
            To evidence.
          </h1>
          <p>
            Plan work. Coordinate specialists. Inspect every action.
            <br />
            Your agents, with you in control.
          </p>
          <div className="auth-flow">
            <span>Objective</span>
            <ChevronRight />
            <span>Agents</span>
            <ChevronRight />
            <span>Verified result</span>
          </div>
        </div>
        <small>LOCAL MODELS · CONTROLLED TOOLS · HUMAN APPROVAL</small>
      </section>
      <section className="auth-form">
        <div className="eyebrow">AGENTFLOW CONTROL CENTER</div>
        <h2>
          {mode === "login"
            ? "Welcome back."
            : "Create your workspace account."}
        </h2>
        <p>
          {mode === "login"
            ? "Sign in to your orchestration workspace."
            : "New accounts receive the Developer role."}
        </p>
        <form onSubmit={submit}>
          <label>
            Email
            <input name="email" type="email" required autoComplete="email" />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              minLength={12}
              maxLength={72}
              required
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
            />
          </label>
          <ErrorBox error={error} />
          <button className="primary" disabled={busy}>
            {busy
              ? "Please wait…"
              : mode === "login"
                ? "Sign in"
                : "Create account"}
            <ArrowUpRight size={17} />
          </button>
        </form>
        <button
          className="text-button"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login"
            ? "Create an account"
            : "Already have an account? Sign in"}
        </button>
        <AccountRecovery />
      </section>
    </main>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null>(null),
    [checking, setChecking] = useState(true);
  const client = useQueryClient();
  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => setToken(""))
      .finally(() => setChecking(false));
  }, []);
  async function logout() {
    try {
      await api("/auth/logout", {});
    } finally {
      setToken("");
      setUser(null);
      client.clear();
    }
  }
  if (checking) return <div className="loading">Connecting to AgentFlow…</div>;
  if (!user) return <Auth onLogin={setUser} />;
  return (
    <div className="shell">
      <aside>
        <Link className="brand" to="/">
          <span>
            <Workflow size={23} />
          </span>
          AgentFlow
        </Link>
        <div className="workspace-label">
          <span className="avatar">AF</span>
          <div>
            Local workspace<small>Autonomous agent platform</small>
          </div>
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map(([label, path, Icon]) => (
            <NavLink key={path} to={path} end={path === "/"}>
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="model-label">
            <i />
            Qwen3 · 8B<small>Configured local model</small>
          </div>
          <button onClick={logout} className="account">
            <span className="avatar">
              {user.email.slice(0, 2).toUpperCase()}
            </span>
            <div>
              {user.email}
              <small>{user.role} · Sign out</small>
            </div>
          </button>
        </div>
      </aside>
      <div className="main">
        <div className="topbar">
          <span>
            Workspace <ChevronRight size={14} /> Control center
          </span>
          <span className="top-note">
            <Command size={14} /> Evidence before action
          </span>
        </div>
        <main>
          {user.forceReset ? (
            <Security onChanged={logout} />
          ) : (
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/runs" element={<Runs />} />
              <Route path="/runs/:id" element={<RunDetail />} />
              <Route path="/approvals" element={<Approvals />} />
              <Route path="/:registry" element={<Registry user={user} />} />
              <Route
                path="/security"
                element={<Security onChanged={logout} />}
              />
              <Route path="/activity" element={<ActivityPage user={user} />} />
            </Routes>
          )}
        </main>
        <footer>
          AgentFlow <span>Every action leaves a trace.</span>
          <span>v0.1 · Local orchestration</span>
        </footer>
      </div>
    </div>
  );
}

function Dashboard() {
  const runs = useList("/runs"),
    agents = useList("/agents"),
    workflows = useList("/workflows");
  const rows = runs.data?.content || [];
  return (
    <>
      <Heading
        eyebrow="WORKSPACE OVERVIEW"
        title="Mission control."
        action={
          <Link className="primary" to="/runs">
            <Plus size={17} />
            New agent run
          </Link>
        }
      >
        Turn an objective into a traceable sequence of work.
      </Heading>
      <ErrorBox error={runs.error || agents.error || workflows.error} />
      <div className="hero">
        <div>
          <span className="eyebrow">BUILT FOR AUTONOMOUS WORK</span>
          <h2>
            Set the objective.
            <br />
            Stay in control.
          </h2>
          <p>
            Specialist agents plan, inspect, and verify.
            <br />
            You decide when sensitive actions move forward.
          </p>
          <Link to="/runs">
            Launch an objective <ArrowUpRight size={16} />
          </Link>
        </div>
        <div className="mini-graph">
          <div className="graph-node">
            <GitBranch />
            Planner <span>01</span>
          </div>
          <div className="graph-branches">
            <div className="graph-node">
              <Box />
              Repository
            </div>
            <div className="graph-node">
              <Shield />
              Security
            </div>
          </div>
          <div className="graph-node final">
            <Check />
            Verified report <span>03</span>
          </div>
          <small>ORCHESTRATION PATTERN · NOT A LIVE RUN</small>
        </div>
      </div>
      <div className="metrics">
        {[
          [
            "Active runs",
            rows.filter((r: any) => !terminal.has(r.status)).length,
            Activity,
          ],
          [
            "Completed",
            rows.filter((r: any) => r.status === "COMPLETED").length,
            Check,
          ],
          [
            "Awaiting approval",
            rows.filter((r: any) => r.status === "WAITING_APPROVAL").length,
            Shield,
          ],
          ["Registered agents", agents.data?.length || 0, Users],
        ].map(([label, value, Icon]: any) => (
          <div className="metric" key={label}>
            <div>
              {label}
              <Icon size={17} />
            </div>
            <strong>{value}</strong>
            <small>
              {label === "Registered agents"
                ? "Configured specialists"
                : "In the latest 25 runs"}
            </small>
          </div>
        ))}
      </div>
      <section className="panel">
        <div className="section-head">
          <h2>
            Recent executions <span>{rows.length}</span>
          </h2>
          <Link to="/runs">
            View runs <ArrowUpRight size={15} />
          </Link>
        </div>
        <RunTable rows={rows} />
      </section>
      <div className="split">
        <section className="panel">
          <div className="section-head">
            <h2>Ready-to-run workflows</h2>
            <Workflow size={17} />
          </div>
          {(workflows.data || []).map((w: any) => (
            <Link key={w.id} to="/runs" className="workflow-row">
              <span className="icon-box">
                <Workflow size={18} />
              </span>
              <div>
                {w.name}
                <small>{w.configuration.agents?.join(" → ")}</small>
              </div>
              <ArrowUpRight size={16} />
            </Link>
          ))}
        </section>
        <section className="panel guardrails">
          <div className="section-head">
            <h2>Execution guardrails</h2>
            <Shield size={17} />
          </div>
          <p>
            <Check /> Workspace boundaries enforced
          </p>
          <p>
            <Check /> Read-only execution by default
          </p>
          <p>
            <Check /> Exact-change approval for edits
          </p>
          <p>
            <Check /> Bounded retries and tool budgets
          </p>
          <div className="notice">
            Runs show measured results. Missing evidence stays visible.
          </div>
        </section>
      </div>
    </>
  );
}
function RunTable({ rows }: { rows: any[] }) {
  return rows.length ? (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Objective</th>
            <th>Status</th>
            <th>Mode</th>
            <th>Started</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>
                <Link to={"/runs/" + r.id}>{r.objective}</Link>
                <small>{r.id.slice(0, 8)}</small>
              </td>
              <td>
                <Badge value={r.status} />
              </td>
              <td className="muted">{r.mode}</td>
              <td className="muted">
                {new Date(r.createdAt).toLocaleString()}
              </td>
              <td>
                <Link to={"/runs/" + r.id}>
                  <ArrowUpRight size={16} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty title="No executions yet" />
  );
}
function Projects() {
  const q = useList("/projects"),
    client = useQueryClient();
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const form = e.currentTarget,
      f = new FormData(form);
    try {
      await api("/projects", Object.fromEntries(f));
      await client.invalidateQueries({ queryKey: ["/projects"] });
      form.reset();
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading eyebrow="APPROVED WORKSPACES" title="Projects.">
        Connect a repository inside your configured workspace root.
      </Heading>
      <ErrorBox error={q.error || error} />
      <div className="split">
        <section className="panel">
          <div className="section-head">
            <h2>Your repositories</h2>
            <Box size={18} />
          </div>
          {q.data?.content?.length ? (
            q.data.content.map((p: any) => (
              <div className="project-card" key={p.id}>
                <Box />
                <h3>{p.name}</h3>
                <p>{p.description || "Local repository"}</p>
                <code>{p.workspacePath}</code>
                <Link to="/runs">
                  Start an analysis <ArrowUpRight size={15} />
                </Link>
              </div>
            ))
          ) : (
            <Empty title="Register your first project" />
          )}
        </section>
        <section className="panel padded">
          <h2>Register workspace</h2>
          <form onSubmit={save}>
            <label>
              Project name
              <input
                name="name"
                required
                maxLength={120}
                placeholder="Payments service"
              />
            </label>
            <label>
              Relative workspace path
              <input
                name="workspacePath"
                required
                placeholder="payments-service"
              />
            </label>
            <p className="muted">
              The folder must already exist under WORKSPACE_ROOT.
            </p>
            <label>
              Description
              <textarea
                name="description"
                maxLength={2000}
                placeholder="What does this project do?"
              />
            </label>
            <button className="primary" disabled={busy}>
              <Plus size={16} />
              Register project
            </button>
          </form>
        </section>
      </div>
    </>
  );
}
function Runs() {
  const [page, setPage] = useState(0);
  const q = useList("/runs?page=" + page),
    projects = useList("/projects"),
    workflows = useList("/workflows"),
    navigate = useNavigate();
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function start(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    try {
      const r = await api("/runs", {
        projectId: f.get("projectId"),
        objective: f.get("objective"),
        mode: f.get("mode"),
        workflowId: f.get("workflowId") || null,
      });
      navigate("/runs/" + r.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading eyebrow="EXECUTION WORKSPACE" title="Agent runs.">
        Define the outcome. Follow every decision and tool result.
      </Heading>
      <ErrorBox error={error || q.error} />
      <section className="panel padded">
        <form onSubmit={start}>
          <div className="form-grid">
            <label>
              Project
              <select name="projectId" required>
                <option value="">Select a project</option>
                {projects.data?.content?.map((p: any) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Workflow
              <select name="workflowId">
                <option value="">Autonomous planning</option>
                {workflows.data
                  ?.filter((w: any) => w.enabled)
                  .map((w: any) => (
                    <option key={w.id} value={w.id}>
                      {w.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Permissions
              <select name="mode">
                <option value="READ_ONLY">Read only</option>
                <option value="EDIT_MODE">Edit mode · approval required</option>
              </select>
            </label>
          </div>
          <label>
            Objective
            <textarea
              name="objective"
              required
              maxLength={4000}
              placeholder="Analyze this repository for production readiness. Inspect architecture, security and dependencies. Reference actual files."
            />
          </label>
          <button className="primary" disabled={busy}>
            <Play size={16} />
            {busy ? "Starting…" : "Launch agent run"}
          </button>
        </form>
      </section>
      <section className="panel">
        <div className="section-head">
          <h2>Execution history</h2>
        </div>
        <RunTable rows={q.data?.content || []} />
        <Pager page={page} total={q.data?.totalPages || 1} onChange={setPage} />
      </section>
    </>
  );
}
function RunDetail() {
  const { id } = useParams();
  const client = useQueryClient();
  const q = useQuery({
    queryKey: ["run", id],
    queryFn: () => api("/runs/" + id),
    refetchInterval: 5000,
  });
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function next() {
      try {
        const value = await stateStream(id!, controller.signal);
        client.setQueryData(["run", id], value);
        if (!terminal.has(value.status) && !controller.signal.aborted)
          timer = setTimeout(next, 2000);
      } catch {
        if (!controller.signal.aborted) timer = setTimeout(next, 5000);
      }
    }
    next();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [id, client]);
  if (!q.data)
    return (
      <>
        <ErrorBox error={q.error} />
        <div className="loading">Loading execution…</div>
      </>
    );
  const r = q.data,
    s = r.state || {};
  async function action(path: string, body: unknown) {
    try {
      await api("/runs/" + id + path, body);
      await q.refetch();
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <Heading
        eyebrow={"EXECUTION / " + id?.slice(0, 8)}
        title={r.objective}
        action={<Badge value={r.status} />}
      >
        Started {new Date(r.createdAt).toLocaleString()} · {r.mode}
      </Heading>
      <ErrorBox error={error || q.error} />
      <div className="run-actions">
        <button
          onClick={() => exportReport(id!).catch((e) => setError(e.message))}
        >
          <FileText size={16} />
          Export Markdown
        </button>
        {!terminal.has(r.status) && (
          <button onClick={() => action("/cancel", {})}>
            <X size={16} />
            Cancel execution
          </button>
        )}
      </div>
      <div className="metrics">
        {[
          ["Tool calls", s.tool_call_count || 0],
          ["LLM calls", s.llm_calls || 0],
          ["Retries", s.retry_count || 0],
          ["Findings", s.findings?.length || 0],
        ].map(([label, value]) => (
          <div className="metric" key={label}>
            <div>{label}</div>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      {s.pending && s.pending.decision === "PENDING" && (
        <section className="panel padded approval">
          <div className="eyebrow">HUMAN DECISION REQUIRED</div>
          <h2>
            {s.pending.request.name} · {s.pending.request.path}
          </h2>
          <p>{s.pending.reason}</p>
          <Badge value={s.pending.risk} />
          <pre>{s.pending.diff}</pre>
          <div className="run-actions">
            <button
              className="primary"
              onClick={() =>
                action("/approval", {
                  approvalId: s.pending.id,
                  approved: true,
                })
              }
            >
              <Check size={16} />
              Approve exact action
            </button>
            <button
              onClick={() =>
                action("/approval", {
                  approvalId: s.pending.id,
                  approved: false,
                })
              }
            >
              Reject
            </button>
          </div>
        </section>
      )}
      <section className="panel">
        <div className="section-head">
          <h2>Task graph</h2>
          <span>
            {s.plan?.filter((t: any) => t.status === "COMPLETED").length || 0} /{" "}
            {s.plan?.length || 0} complete
          </span>
        </div>
        <div className="task-graph">
          {s.plan?.map((t: any) => (
            <div className={"task-node " + t.status.toLowerCase()} key={t.id}>
              <span className="eyebrow">{t.agent}</span>
              <h3>{t.objective}</h3>
              <Badge value={t.status} />
              <small>
                {t.dependencies?.length
                  ? "After: " + t.dependencies.join(", ")
                  : "Entry task"}
              </small>
            </div>
          ))}
        </div>
      </section>
      <div className="split">
        <section className="panel">
          <div className="section-head">
            <h2>Execution timeline</h2>
          </div>
          <div className="timeline">
            {s.events
              ?.slice()
              .reverse()
              .map((e: any) => (
                <div key={e.id}>
                  <i />
                  <div>
                    <strong>{e.type.replaceAll("_", " ")}</strong>
                    <p>{e.detail}</p>
                    <small>
                      {new Date(e.time * 1000).toLocaleTimeString()}
                    </small>
                  </div>
                </div>
              ))}
          </div>
        </section>
        <section className="panel">
          <div className="section-head">
            <h2>Evidence & findings</h2>
          </div>
          <div className="padded">
            {s.findings?.map((f: any, i: number) => (
              <article className="finding" key={i}>
                <Badge value={f.severity} />
                <h3>{f.title}</h3>
                <p>{f.description}</p>
                <code>{f.affected_file}</code>
                <p>{f.recommendation}</p>
              </article>
            ))}
            {s.tool_results?.map((t: any) => (
              <details key={t.id}>
                <summary>
                  {t.tool} <Badge value={t.status} />
                </summary>
                <pre>{JSON.stringify(t.output, null, 2)}</pre>
              </details>
            ))}
            {s.errors?.map((e: string, i: number) => (
              <div className="error" key={i}>
                {e}
              </div>
            ))}
          </div>
        </section>
      </div>
      {s.report && (
        <section className="panel padded">
          <h2>Final report</h2>
          <pre className="report">{s.report}</pre>
        </section>
      )}
    </>
  );
}
function Approvals() {
  const [page, setPage] = useState(0);
  const q = useList("/approvals?page=" + page);
  const rows = q.data?.content || [];
  return (
    <>
      <Heading eyebrow="HUMAN OVERSIGHT" title="Approval center.">
        Inspect the proposed action and evidence before granting permission.
      </Heading>
      <ErrorBox error={q.error} />
      <section className="panel">
        <RunTable rows={rows} />
        {!rows.length && (
          <p className="padded muted">No pending approvals on this page.</p>
        )}
        <Pager page={page} total={q.data?.totalPages || 1} onChange={setPage} />
      </section>
    </>
  );
}
function Registry({ user }: { user: User }) {
  const { registry } = useParams();
  const q = useList("/" + registry),
    client = useQueryClient();
  const [error, setError] = useState("");
  if (!["agents", "tools", "workflows"].includes(registry || ""))
    return <Empty title="Page not found" />;
  async function toggle(d: any) {
    try {
      await api("/" + registry, {
        name: d.name,
        configuration: d.configuration,
        enabled: !d.enabled,
      });
      client.invalidateQueries({ queryKey: ["/" + registry] });
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await api("/" + registry, {
        name: f.get("name"),
        configuration: JSON.parse(String(f.get("configuration"))),
        enabled: true,
      });
      client.invalidateQueries({ queryKey: ["/" + registry] });
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <Heading
        eyebrow="PLATFORM REGISTRY"
        title={registry![0].toUpperCase() + registry!.slice(1) + "."}
      >
        Explicit capabilities. Controlled permissions. Versioned configuration.
      </Heading>
      <ErrorBox error={q.error || error} />
      {registry === "workflows" &&
        ["ADMIN", "DEVELOPER"].includes(user.role) && <WorkflowBuilder />}
      <div className="registry-grid">
        {Array.isArray(q.data) &&
          q.data.map((d: any) => (
            <section className="panel padded" key={d.id}>
              <div className="section-head compact">
                <span className="icon-box">
                  {registry === "agents" ? (
                    <Users size={19} />
                  ) : registry === "tools" ? (
                    <Terminal size={19} />
                  ) : (
                    <Workflow size={19} />
                  )}
                </span>
                <Badge value={d.enabled ? "ENABLED" : "DISABLED"} />
              </div>
              <h2>{d.name}</h2>
              <p>{d.configuration.description || d.configuration.objective}</p>
              {d.configuration.risk_level && (
                <Badge value={d.configuration.risk_level} />
              )}
              <div className="chips">
                {(
                  d.configuration.available_tools ||
                  d.configuration.agents ||
                  d.configuration.permissions ||
                  []
                ).map((t: string, i: number) => (
                  <span key={i}>{t}</span>
                ))}
              </div>
              <p className="muted">
                Revision {d.revision}
                {d.configuration.timeout
                  ? " · " + d.configuration.timeout + "s timeout"
                  : ""}
              </p>
              {user.role === "ADMIN" && (
                <button onClick={() => toggle(d)}>
                  {d.enabled ? "Disable" : "Enable"}
                </button>
              )}
            </section>
          ))}
      </div>
      {user.role === "ADMIN" && (
        <section className="panel padded">
          <h2>Create or update a definition</h2>
          <form onSubmit={save}>
            <label>
              Name
              <input name="name" required />
            </label>
            <label>
              Configuration JSON
              <textarea
                className="code"
                name="configuration"
                required
                defaultValue={
                  registry === "workflows"
                    ? '{"agents":["REPOSITORY","SECURITY","REVIEWER","REPORTER"]}'
                    : "{}"
                }
              />
            </label>
            <button className="primary">Save revision</button>
          </form>
        </section>
      )}
    </>
  );
}
function Security({ onChanged }: { onChanged: () => void }) {
  const [error, setError] = useState("");
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    try {
      await api(
        "/auth/password",
        Object.fromEntries(new FormData(e.currentTarget)),
      );
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <Heading eyebrow="ACCOUNT SETTINGS" title="Security.">
        Changing your password revokes all active sessions.
      </Heading>
      <section className="panel padded narrow">
        <ErrorBox error={error} />
        <form onSubmit={save}>
          <label>
            Current password
            <input
              type="password"
              name="currentPassword"
              required
              autoComplete="current-password"
            />
          </label>
          <label>
            New password
            <input
              type="password"
              name="newPassword"
              minLength={12}
              maxLength={72}
              required
              autoComplete="new-password"
            />
          </label>
          <button className="primary">Change password & sign out</button>
        </form>
      </section>
    </>
  );
}
function ActivityPage({ user }: { user: User }) {
  const q = useQuery({
    queryKey: ["/audit"],
    queryFn: () => api("/audit"),
    enabled: user.role === "ADMIN",
  });
  return (
    <>
      <Heading eyebrow="ACCOUNTABILITY" title="Audit trail.">
        Durable records of platform actions.
      </Heading>
      <ErrorBox error={q.error} />
      <section className="panel">
        {user.role !== "ADMIN" ? (
          <Empty title="Administrator access required">
            Run participants can inspect their own execution timelines.
          </Empty>
        ) : (
          <div className="timeline">
            {q.data?.content?.map((a: any) => (
              <div key={a.id}>
                <i />
                <div>
                  <strong>{a.action}</strong>
                  <p>{a.detail}</p>
                  <small>
                    {new Date(a.createdAt).toLocaleString()} · {a.resource}
                  </small>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function WorkflowBuilder() {
  const agents = useList("/agents"),
    client = useQueryClient();
  const [nodes, setNodes] = useState([
    "REPOSITORY",
    "SECURITY",
    "REVIEWER",
    "REPORTER",
  ]);
  const [error, setError] = useState(""),
    [saved, setSaved] = useState("");
  function move(index: number, delta: number) {
    const next = [...nodes],
      target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setNodes(next);
  }
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const name = new FormData(e.currentTarget).get("name");
    try {
      await api("/workflows", {
        name,
        configuration: { agents: nodes },
        enabled: true,
      });
      await client.invalidateQueries({ queryKey: ["/workflows"] });
      setSaved("Workflow saved. Select it when launching a run.");
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <section className="panel padded">
      <div className="section-head compact">
        <h2>Workflow builder</h2>
        <Badge value="GUIDED" />
      </div>
      <p>
        Arrange specialists in execution order. Each step depends on the
        previous step.
      </p>
      <ErrorBox error={error} />
      {saved && <p role="status">{saved}</p>}
      <div className="task-graph">
        {nodes.map((name, index) => (
          <div className="task-node" key={index}>
            <span className="eyebrow">STEP {index + 1}</span>
            <label>
              Agent
              <select
                aria-label={"Agent for step " + (index + 1)}
                value={name}
                onChange={(e) =>
                  setNodes(
                    nodes.map((n, i) => (i === index ? e.target.value : n)),
                  )
                }
              >
                {(agents.data || [])
                  .filter((a: any) => a.enabled && a.name !== "PLANNER")
                  .map((a: any) => (
                    <option key={a.id} value={a.name}>
                      {a.name}
                    </option>
                  ))}
              </select>
            </label>
            <div className="run-actions">
              <button
                type="button"
                aria-label={"Move step " + (index + 1) + " earlier"}
                disabled={!index}
                onClick={() => move(index, -1)}
              >
                ←
              </button>
              <button
                type="button"
                aria-label={"Move step " + (index + 1) + " later"}
                disabled={index === nodes.length - 1}
                onClick={() => move(index, 1)}
              >
                →
              </button>
              <button
                type="button"
                aria-label={"Remove step " + (index + 1)}
                disabled={nodes.length === 1}
                onClick={() => setNodes(nodes.filter((_, i) => i !== index))}
              >
                <X size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>
      <button
        type="button"
        disabled={nodes.length >= 12}
        onClick={() => setNodes([...nodes, "REVIEWER"])}
      >
        <Plus size={14} />
        Add agent step
      </button>
      <form onSubmit={save} style={{ marginTop: 18 }}>
        <label>
          Workflow name
          <input
            name="name"
            required
            maxLength={120}
            placeholder="My production review"
          />
        </label>
        <button className="primary">Save workflow</button>
      </form>
    </section>
  );
}

function AccountRecovery() {
  const [tokenMode, setTokenMode] = useState(false);
  const [error, setError] = useState(""),
    [message, setMessage] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setMessage("");
    const input = Object.fromEntries(new FormData(e.currentTarget));
    try {
      const result = await api(
        tokenMode ? "/auth/reset-password" : "/auth/forgot-password",
        input,
      );
      setMessage(
        result.message || "Password changed. Sign in with your new password.",
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <details>
      <summary>Recover your account</summary>
      <p>Recovery uses a one-time token delivered by your administrator.</p>
      <form onSubmit={submit}>
        {tokenMode ? (
          <>
            <label>
              Reset token
              <input name="token" required autoComplete="off" />
            </label>
            <label>
              New password
              <input
                name="password"
                type="password"
                minLength={12}
                maxLength={72}
                required
                autoComplete="new-password"
              />
            </label>
          </>
        ) : (
          <label>
            Account email
            <input name="email" type="email" required autoComplete="email" />
          </label>
        )}
        <ErrorBox error={error} />
        {message && <p role="status">{message}</p>}
        <button type="submit">
          {tokenMode ? "Reset password" : "Request recovery"}
        </button>
        <button
          type="button"
          className="text-button"
          onClick={() => {
            setTokenMode(!tokenMode);
            setError("");
            setMessage("");
          }}
        >
          {tokenMode ? "Request a token" : "I have a reset token"}
        </button>
      </form>
    </details>
  );
}

function Pager({
  page,
  total,
  onChange,
}: {
  page: number;
  total: number;
  onChange: (page: number) => void;
}) {
  return total > 1 ? (
    <div className="padded run-actions">
      <button disabled={page === 0} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      <span className="muted">
        Page {page + 1} of {total}
      </span>
      <button disabled={page + 1 >= total} onClick={() => onChange(page + 1)}>
        Next
      </button>
    </div>
  ) : null;
}
