"""In-memory fake of the Supabase AsyncClient for offline testing.

Implements the subset of the PostgREST query API that the repositories and
services use, plus the application RPC functions. Data lives in ``self.tables``
as ``{table_name: [row_dict, ...]}``. ``execute()`` returns an object exposing
``.data`` similar to ``postgrest.APIResponse``.
"""

from __future__ import annotations

import copy
import json


class _Response:
    def __init__(self, data):
        self.data = data


class _QueryBuilder:
    """Chainable filter/limiter with a terminal ``execute()``."""

    def __init__(self, fake, table_name, columns=None, action="select"):
        self._fake = fake
        self._table = table_name
        self._columns = columns or ["*"]
        self._action = action  # "select" | "insert" | "update" | "delete"
        self._filters = []  # list of (col, op, value)
        self._orders = []  # list of (col, desc)
        self._limit = None
        self._payload = None
        self._single = False

    # -- filters ----------------------------------------------------------
    def eq(self, col, value):
        self._filters.append((col, "==", value))
        return self

    def neq(self, col, value):
        self._filters.append((col, "!=", value))
        return self

    def in_(self, col, values):
        self._filters.append((col, "in", list(values)))
        return self

    def is_(self, col, value):
        self._filters.append((col, "is", value))
        return self

    def gt(self, col, value):
        self._filters.append((col, ">", value))
        return self

    def gte(self, col, value):
        self._filters.append((col, ">=", value))
        return self

    def lt(self, col, value):
        self._filters.append((col, "<", value))
        return self

    def lte(self, col, value):
        self._filters.append((col, "<=", value))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def offset(self, n):
        return self

    def order(self, col, *, desc=False, foreign_table=None, nullsfirst=None, nullslast=None):
        self._orders.append((col, desc))
        return self

    def maybe_single(self):
        self._single = True
        self._limit = 1
        return self

    def single(self):
        self._single = True
        self._limit = 1
        return self

    def select(self, *cols):
        if cols:
            self._columns = list(cols)
        return self

    # -- mutations --------------------------------------------------------
    def insert(self, payload, *, returning="representation", count=None):
        self._action = "insert"
        self._payload = payload
        return self

    def update(self, payload, *, count=None):
        self._action = "update"
        self._payload = payload
        return self

    def delete(self, *, count=None, returning="representation"):
        self._action = "delete"
        return self

    def upsert(self, payload, *args, **kwargs):
        self._action = "upsert"
        self._payload = payload
        return self

    # -- execution --------------------------------------------------------
    def _match(self, row):
        for col, op, value in self._filters:
            actual = row.get(col)
            if op == "==":
                if actual != value:
                    return False
            elif op == "!=":
                if actual == value:
                    return False
            elif op == "in":
                if actual not in value:
                    return False
            elif op == "is":
                if value is None:
                    if actual is not None:
                        return False
                else:
                    if actual != value:
                        return False
            elif op == ">":
                if actual is None or not (actual > value):
                    return False
            elif op == ">=":
                if actual is None or not (actual >= value):
                    return False
            elif op == "<":
                if actual is None or not (actual < value):
                    return False
            elif op == "<=":
                if actual is None or not (actual <= value):
                    return False
        return True

    async def execute(self):
        if self._action.startswith("rpc:"):
            fn = self._action.split(":", 1)[1]
            return self._fake._run_rpc(fn, self._payload)

        table = self._fake.tables.setdefault(self._table, [])

        if self._action == "insert":
            inserted = []
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            for payload in payloads:
                row = dict(payload)
                row.setdefault("id", self._fake.next_id())
                table.append(copy.deepcopy(row))
                inserted.append(copy.deepcopy(row))
            return _Response(inserted)

        if self._action == "update":
            updated = []
            for row in table:
                if self._match(row):
                    row.update(copy.deepcopy(self._payload))
                    updated.append(copy.deepcopy(row))
            return _Response(updated)

        if self._action == "delete":
            kept = []
            deleted = []
            for row in table:
                if self._match(row):
                    deleted.append(copy.deepcopy(row))
                else:
                    kept.append(row)
            table[:] = kept
            return _Response(deleted)

        # select
        rows = [copy.deepcopy(row) for row in table if self._match(row)]
        for col, desc in self._orders:
            rows.sort(key=lambda r: r.get(col), reverse=desc)
        if self._limit is not None:
            rows = rows[: self._limit]

        if self._single:
            return _Response(rows[0] if rows else None)

        if self._columns == ["*"]:
            return _Response(rows)
        projected = [
            {c: row.get(c) for c in self._columns if c in row}
            for row in rows
        ]
        return _Response(projected)


class FakeSupabaseClient:
    """In-memory stand-in for ``supabase.AsyncClient``."""

    def __init__(self):
        self.tables: dict[str, list[dict]] = {}
        self._counter = 1000
        self.calls: list[str] = []

    def next_id(self) -> int:
        self._counter += 1
        return self._counter

    # -- PostgREST-style table access -------------------------------------
    def table(self, table_name: str) -> _QueryBuilder:
        self.calls.append(f"table:{table_name}")
        return _QueryBuilder(self, table_name)

    def from_(self, table_name: str) -> _QueryBuilder:
        return self.table(table_name)

    # -- RPC -----------------------------------------------------------------
    def rpc(self, fn_name: str, params: dict) -> _QueryBuilder:
        self.calls.append(f"rpc:{fn_name}")
        builder = _QueryBuilder(self, "$rpc", action=f"rpc:{fn_name}")
        builder._payload = params
        return builder

    def _run_rpc(self, fn_name: str, params: dict) -> _Response:
        handler = getattr(self, f"_rpc_{fn_name}", None)
        if handler is None:
            raise NotImplementedError(f"RPC {fn_name} not implemented in fake")
        return handler(params)

    # -- RPC implementations ----------------------------------------------

    def _rpc_pop_queue_entries(self, params) -> _Response:
        guild_id = params["p_guild_id"]
        queue = self.tables.setdefault("queue_entries", [])
        popped = [row["player_id"] for row in queue
                  if row.get("guild_id") == guild_id and row.get("status") == "WAITING"]
        self.tables["queue_entries"] = [
            row for row in queue
            if not (row.get("guild_id") == guild_id and row.get("status") == "WAITING")
        ]
        return _Response(popped)

    def _rpc_create_match(self, params) -> _Response:
        guild_id = params["p_guild_id"]
        player_ids = json.loads(params["p_player_ids"])
        matches = self.tables.setdefault("matches", [])
        match_id = self.next_id()
        seq = len(matches) + 1
        match = {
            "id": match_id,
            "guild_id": guild_id,
            "display_id": f"AU-{seq:08d}",
            "status": "CREATING",
            "result_processed": False,
            "average_elo": None,
        }
        matches.append(match)
        mp_rows = self.tables.setdefault("match_players", [])
        elo_sum = 0
        players = self.tables.setdefault("players", [])
        for idx, pid in enumerate(player_ids, start=1):
            elo = 1000
            for p in players:
                if p.get("id") == pid:
                    elo = p.get("elo", 1000)
                    break
            elo_sum += elo
            mp_rows.append({
                "id": self.next_id(),
                "match_id": match_id,
                "player_id": pid,
                "call_number": idx,
                "elo_before": elo,
                "role_side": None,
                "result": None,
            })
        match["average_elo"] = elo_sum // len(player_ids) if player_ids else 0
        return _Response([copy.deepcopy(match)])

    def _rpc_apply_match_result(self, params) -> _Response:
        players_list = json.loads(params["p_players"])
        winner_side = params["p_winner_side"]
        win_delta = params["p_win_delta"]
        loss_delta = params["p_loss_delta"]
        match_id = params.get("p_match_id")
        approved_by = params.get("p_approved_by")
        guild_id = params["p_guild_id"]
        players = self.tables.setdefault("players", [])
        txs = self.tables.setdefault("elo_transactions", [])
        changes = []
        for item in players_list:
            delta = win_delta if item["role_side"] == winner_side else loss_delta
            for p in players:
                if p.get("id") == item["player_id"]:
                    old_elo = p.get("elo", item.get("elo_before", 1000))
                    new_elo = old_elo + delta
                    p["elo"] = new_elo
                    p["peak_elo"] = max(p.get("peak_elo", old_elo), new_elo)
                    txs.append({
                        "id": self.next_id(),
                        "guild_id": guild_id,
                        "player_id": p["id"],
                        "match_id": match_id,
                        "old_elo": old_elo,
                        "change": delta,
                        "new_elo": new_elo,
                        "reason": f"Match {winner_side}",
                        "transaction_type": "MATCH",
                        "created_by": approved_by,
                    })
                    changes.append(p["id"])
                    break
        return _Response(changes)

    def _rpc_submit_match_result(self, params) -> _Response:
        guild_id = params["p_guild_id"]
        match_id = params["p_match_id"]
        sub = {
            "id": self.next_id(),
            "match_id": match_id,
            "guild_id": guild_id,
            "submitted_by": params["p_submitted_by"],
            "winner_side": params["p_winner_side"],
            "impostor_player_ids": params["p_impostor_player_ids"],
            "screenshot_url": params.get("p_screenshot_url"),
            "status": "PENDING",
            "submitted_at": None,
        }
        self.tables.setdefault("result_submissions", []).append(sub)
        for m in self.tables.setdefault("matches", []):
            if m.get("id") == match_id:
                m["status"] = "RESULT_PENDING"
                m["result_submitted_by"] = params["p_submitted_by"]
        return _Response([copy.deepcopy(sub)])

    def _rpc_approve_match_result(self, params) -> _Response:
        match_id = params["p_match_id"]
        approved_by = params["p_approved_by"]
        win_elo = params["p_win_elo"]
        loss_elo = params["p_loss_elo"]
        subs = self.tables.setdefault("result_submissions", [])
        sub = next((s for s in subs if s.get("match_id") == match_id and s.get("status") == "PENDING"), None)
        if sub is None:
            raise ValueError("No pending result submission")
        impostor_ids = set(int(x) for x in sub["impostor_player_ids"].split(",") if x)
        mp_rows = [r for r in self.tables.setdefault("match_players", []) if r.get("match_id") == match_id]
        players_list = []
        for mp in mp_rows:
            role_side = "IMPOSTOR" if mp["player_id"] in impostor_ids else "CREWMATE"
            mp["role_side"] = role_side
            players_list.append({
                "player_id": mp["player_id"],
                "elo_before": mp.get("elo_before"),
                "role_side": role_side,
            })
        match = next((m for m in self.tables.setdefault("matches", []) if m.get("id") == match_id), None)
        guild_id = match.get("guild_id") if match else sub["guild_id"]
        sub["status"] = "APPROVED"
        sub["approved_by"] = approved_by
        sub["approved_at"] = None
        if match:
            match["result_processed"] = True
            match["result_approved_by"] = approved_by
            match["status"] = "COMPLETED"
            match["winner_side"] = sub["winner_side"]
        self._rpc_apply_match_result({
            "p_guild_id": guild_id,
            "p_players": json.dumps(players_list),
            "p_winner_side": sub["winner_side"],
            "p_win_delta": win_elo,
            "p_loss_delta": loss_elo,
            "p_match_id": match_id,
            "p_approved_by": approved_by,
        })
        return _Response([])
