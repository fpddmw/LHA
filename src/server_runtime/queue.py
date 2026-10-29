"""Transactional queue on local disk. One service owns external execution per host."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import time

from planner_harness.execution import signature


class Queue:
    def __init__(self, path, limits=None):
        self.path = Path(path)
        if os.name == "nt" and str(self.path.resolve()).startswith("\\\\"):
            raise ValueError("Queue database must be on local disk, not a UNC/network share")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                  id INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL, kind TEXT NOT NULL,
                  resource TEXT NOT NULL, payload TEXT NOT NULL, signature TEXT NOT NULL,
                  priority INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
                  owner TEXT, attempt INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL,
                  started REAL, finished REAL, result TEXT, error TEXT, expanded INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS dependencies (
                  job INTEGER NOT NULL REFERENCES jobs(id), parent INTEGER NOT NULL REFERENCES jobs(id),
                  PRIMARY KEY(job,parent));
                CREATE TABLE IF NOT EXISTS attempts (
                  job INTEGER, attempt INTEGER, owner TEXT, started REAL, finished REAL,
                  outcome TEXT, reason TEXT, authorization TEXT, PRIMARY KEY(job,attempt));
            """)
            row = db.execute("SELECT value FROM settings WHERE key='limits'").fetchone()
            limits = limits or (json.loads(row[0]) if row else {"llm": 2, "gpu": 1, "cpu": 2})
            if set(limits) != {"llm", "gpu", "cpu"} or any(type(v) is not int or v < 1 for v in limits.values()) or limits["gpu"] != 1:
                raise ValueError("Use positive resource limits and one generation slot per service")
            encoded = json.dumps(limits, sort_keys=True)
            if row and row[0] != encoded:
                raise ValueError("Queue resource limits are frozen; drain and create a new service for changes")
            db.execute("INSERT OR IGNORE INTO settings VALUES ('limits',?)", (encoded,))
            self.limits = limits
            db.execute("INSERT OR IGNORE INTO settings VALUES ('dispatch','running')")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    @staticmethod
    def decode(row):
        if row is None:
            return None
        result = dict(row)
        for key in ("payload", "result"):
            result[key] = json.loads(result[key]) if result[key] is not None else None
        return result

    def enqueue(self, key, kind, resource, payload, *, parents=(), priority=10):
        if resource not in self.limits:
            raise ValueError("Unknown resource")
        parents = sorted(set(parents))
        sig = signature({"kind": kind, "resource": resource, "payload": payload, "parents": parents, "priority": priority})
        with self.transaction() as db:
            existing = db.execute("SELECT * FROM jobs WHERE key=?", (key,)).fetchone()
            if existing:
                if existing["signature"] != sig:
                    raise ValueError("Idempotency key reused with different inputs")
                return existing["id"]
            for parent in parents:
                if not db.execute("SELECT id FROM jobs WHERE id=?", (parent,)).fetchone():
                    raise ValueError("Dependencies must already exist; forward references/cycles are not allowed")
            cursor = db.execute("INSERT INTO jobs(key,kind,resource,payload,signature,priority,created) VALUES(?,?,?,?,?,?,?)",
                                (key, kind, resource, json.dumps(payload, ensure_ascii=False), sig, priority, time.time()))
            identity = cursor.lastrowid
            db.executemany("INSERT INTO dependencies VALUES(?,?)", [(identity, p) for p in parents])
            return identity

    def claim(self, resource, owner):
        with self.transaction() as db:
            if db.execute("SELECT value FROM settings WHERE key='dispatch'").fetchone()[0] != "running":
                return None
            active = db.execute("SELECT COUNT(*) FROM jobs WHERE resource=? AND state='running'", (resource,)).fetchone()[0]
            if active >= self.limits[resource]:
                return None
            # Age increases priority gradually, so final reviews are not starved by new online tasks.
            row = db.execute("""SELECT * FROM jobs j WHERE resource=? AND state='queued'
                AND NOT EXISTS (SELECT 1 FROM dependencies d JOIN jobs p ON p.id=d.parent
                                WHERE d.job=j.id AND p.state!='complete')
                ORDER BY priority - ((? - created) / 120.0), id LIMIT 1""", (resource, time.time())).fetchone()
            if not row:
                return None
            now = time.time()
            attempt = row["attempt"] + 1
            db.execute("UPDATE jobs SET state='running',owner=?,attempt=?,started=?,finished=NULL WHERE id=?",
                       (owner, attempt, now, row["id"]))
            db.execute("INSERT INTO attempts(job,attempt,owner,started,authorization) VALUES(?,?,?,?,?)", (row["id"], attempt, owner, now, row["error"]))
            return self.decode(db.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone())

    def finish(self, job, *, result=None, error=None, state=None):
        state = state or ("failed" if error else "complete")
        if state not in {"complete", "failed", "needs_review"}:
            raise ValueError("Invalid terminal queue state")
        with self.transaction() as db:
            now = time.time()
            changed = db.execute("""UPDATE jobs SET state=?,result=?,error=?,finished=?
                WHERE id=? AND state='running' AND owner=? AND attempt=?""",
                (state, json.dumps(result, ensure_ascii=False) if result is not None else None, error, now,
                 job["id"], job["owner"], job["attempt"])).rowcount
            if changed != 1:
                raise ValueError("Stale completion rejected")
            db.execute("UPDATE attempts SET finished=?,outcome=?,reason=? WHERE job=? AND attempt=?",
                       (now, state, error, job["id"], job["attempt"]))

    def recover(self):
        """Only call while holding the exclusive service OS lock. Receipts are reconciled by executor."""
        with self.transaction() as db:
            db.execute("UPDATE attempts SET finished=?,outcome='interrupted' WHERE outcome IS NULL", (time.time(),))
            db.execute("UPDATE jobs SET state='queued',owner=NULL WHERE state='running'")

    def retry(self, identity, reason):
        if not reason.strip():
            raise ValueError("Explicit retry reason required")
        with self.transaction() as db:
            row = db.execute("SELECT state FROM jobs WHERE id=?", (identity,)).fetchone()
            if not row or row[0] not in {"failed", "needs_review"}:
                raise ValueError("Retry only a stopped job after checking its receipts")
            db.execute("UPDATE jobs SET state='queued',owner=NULL,error=? WHERE id=?", ("retry authorized: " + reason, identity))

    def rows(self):
        with self.connect() as db:
            return [self.decode(r) for r in db.execute("SELECT * FROM jobs ORDER BY id")]

    def pending_expansions(self):
        with self.connect() as db:
            return [self.decode(r) for r in db.execute("SELECT * FROM jobs WHERE state='complete' AND expanded=0 ORDER BY id")]

    def summary(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT id,key,kind,resource,state,attempt,created,started,finished,error FROM jobs ORDER BY id")]

    def expanded(self, identity):
        with self.connect() as db:
            db.execute("UPDATE jobs SET expanded=1 WHERE id=? AND state='complete'", (identity,))

    def dispatch(self, value=None):
        with self.transaction() as db:
            if value is not None:
                if value not in {"running", "drain"}:
                    raise ValueError("Dispatch must be running or drain")
                db.execute("UPDATE settings SET value=? WHERE key='dispatch'", (value,))
            return db.execute("SELECT value FROM settings WHERE key='dispatch'").fetchone()[0]

    def status(self):
        with self.connect() as db:
            db.execute("BEGIN")
            rows = [self.decode(r) for r in db.execute("SELECT * FROM jobs ORDER BY id")]
            deps = list(db.execute("SELECT job,parent FROM dependencies"))
            states = {r["id"]: r["state"] for r in rows}
            for r in rows:
                r["blocked_by"] = [d["parent"] for d in deps if d["job"] == r["id"] and states[d["parent"]] != "complete"]
                r["attempts"] = [dict(a) for a in db.execute("SELECT * FROM attempts WHERE job=? ORDER BY attempt", (r["id"],))]
            return {"dispatch": db.execute("SELECT value FROM settings WHERE key='dispatch'").fetchone()[0], "limits": self.limits, "jobs": rows}
