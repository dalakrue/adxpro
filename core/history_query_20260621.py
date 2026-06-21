"""Bounded completed-H1 history projection helpers.

DuckDB is used when available so column projection, time predicates and LIMIT are
pushed into the vectorized query. A vectorized pandas fallback preserves the
same result contract for minimal test environments.
"""
from __future__ import annotations

from typing import Iterable
import pandas as pd

_TIME_ALIASES = ("Time", "time", "Datetime", "DateTime", "Timestamp", "Date", "Hour", "candle time")
_DUCKDB_MIN_ROWS = 5_000  # avoid connection/import overhead on ordinary 25-day H1 views


def time_column(frame: pd.DataFrame) -> str | None:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    lookup = {str(c).strip().lower(): str(c) for c in frame.columns}
    for name in _TIME_ALIASES:
        hit = lookup.get(name.lower())
        if hit:
            return hit
    return None


def _requested_columns(frame: pd.DataFrame, columns: Iterable[str] | None, time_col: str | None) -> list[str]:
    if columns is None:
        chosen = [str(c) for c in frame.columns]
    else:
        wanted = {str(c) for c in columns}
        chosen = [str(c) for c in frame.columns if str(c) in wanted]
    if time_col and time_col not in chosen:
        chosen.insert(0, time_col)
    return chosen


def project_completed_h1(
    frame: pd.DataFrame,
    *,
    days: int = 25,
    columns: Iterable[str] | None = None,
    maximum_rows: int = 600,
    completed_h1: object | None = None,
    descending: bool = True,
) -> pd.DataFrame:
    """Return a shallow, bounded, selected-column, completed-H1 history view."""
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame()
    tcol = time_column(frame)
    selected = _requested_columns(frame, columns, tcol)
    if not selected:
        return pd.DataFrame(index=frame.index[:0])

    completed = pd.to_datetime(completed_h1, errors="coerce", utc=True)
    if pd.isna(completed):
        completed = None

    # DuckDB pushdown is valuable for genuinely large histories. Ordinary H1
    # 25-day views are small enough that a vectorized shallow pandas projection
    # avoids the in-process connection/import overhead and phone/server heat.
    if tcol and len(frame) >= _DUCKDB_MIN_ROWS:
        try:
            import duckdb  # type: ignore

            conn = duckdb.connect(database=":memory:")
            try:
                conn.register("history_source", frame)
                qcols = ", ".join('"' + c.replace('"', '""') + '"' for c in selected)
                qt = '"' + tcol.replace('"', '""') + '"'
                parsed = pd.to_datetime(frame[tcol], errors="coerce", utc=True)
                latest = completed if completed is not None else (parsed.max() if parsed.notna().any() else None)
                params: list[object] = []
                where: list[str] = [f"TRY_CAST({qt} AS TIMESTAMPTZ) IS NOT NULL"]
                if latest is not None and not pd.isna(latest):
                    where.append(f"TRY_CAST({qt} AS TIMESTAMPTZ) <= ?")
                    params.append(latest.to_pydatetime())
                    where.append(f"TRY_CAST({qt} AS TIMESTAMPTZ) >= ?")
                    params.append((latest - pd.Timedelta(days=max(1, int(days)))).to_pydatetime())
                order = "DESC" if descending else "ASC"
                sql = f"SELECT {qcols} FROM history_source WHERE {' AND '.join(where)} ORDER BY TRY_CAST({qt} AS TIMESTAMPTZ) {order} LIMIT ?"
                params.append(max(1, int(maximum_rows)))
                return conn.execute(sql, params).fetch_df()
            finally:
                conn.close()
        except Exception:
            pass

    work = frame.loc[:, selected].copy(deep=False)
    if not tcol:
        return work.tail(maximum_rows).iloc[::-1].reset_index(drop=True) if descending else work.tail(maximum_rows).reset_index(drop=True)
    parsed = pd.to_datetime(work[tcol], errors="coerce", utc=True)
    latest = completed if completed is not None else (parsed.max() if parsed.notna().any() else None)
    mask = parsed.notna()
    if latest is not None and not pd.isna(latest):
        mask &= parsed.le(latest) & parsed.ge(latest - pd.Timedelta(days=max(1, int(days))))
    work = work.loc[mask]
    parsed = parsed.loc[mask]
    if work.empty:
        return work.reset_index(drop=True)
    order = parsed.sort_values(ascending=not descending, kind="mergesort").index
    return work.loc[order].head(maximum_rows).reset_index(drop=True)


__all__ = ["project_completed_h1", "time_column"]
