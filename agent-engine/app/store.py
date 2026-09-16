import copy
import threading
from sqlalchemy import create_engine, MetaData, Table, Column, String, JSON, select, update

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}

class Store:
    """Node-boundary snapshots. A deployment uses one engine process; DB outlives it."""
    def __init__(self, url):
        self.engine = create_engine(url, pool_pre_ping=True)
        self.lock = threading.RLock()
        meta = MetaData()
        self.runs = Table("engine_runs", meta, Column("id", String(36), primary_key=True),
                          Column("state", JSON, nullable=False))
        meta.create_all(self.engine)

    def get(self, run_id):
        with self.engine.connect() as c:
            row = c.execute(select(self.runs.c.state).where(self.runs.c.id == run_id)).first()
            return copy.deepcopy(row[0]) if row else None

    def create(self, state):
        with self.lock, self.engine.begin() as c:
            c.execute(self.runs.insert().values(id=state["run_id"], state=state))

    def save(self, state):
        with self.lock, self.engine.begin() as c:
            previous = c.execute(select(self.runs.c.state).where(self.runs.c.id == state["run_id"])).scalar_one()
            if previous.get("status") == "CANCELLED":
                return
            c.execute(update(self.runs).where(self.runs.c.id == state["run_id"]).values(state=state))

    def cancel(self, run_id):
        with self.lock:
            state = self.get(run_id)
            if state is None:
                raise KeyError(run_id)
            if state["status"] in TERMINAL:
                return state
            state["status"] = "CANCELLED"
            self.save(state)
            return state

    def recover(self):
        # Never replay a possibly executed mutation after a crash.
        with self.engine.connect() as c:
            states = list(c.execute(select(self.runs.c.state)).scalars())
        for state in states:
            if state["status"] not in TERMINAL | {"WAITING_APPROVAL"}:
                state["status"] = "FAILED"
                state["errors"].append("ENGINE_RESTARTED: interrupted run requires a new execution")
                self.save(state)
