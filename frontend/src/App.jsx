import React, { useEffect, useMemo, useState } from "react";
import "./App.css";

export default function App() {
  const [position, setPosition] = useState("QB");
  const [year, setYear] = useState("2024");
  const [week, setWeek] = useState("1");
  const [view, setView] = useState("weekly"); // "weekly" or "season"
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: null, dir: "asc" });

  const positionOptions = ["QB", "RB", "WR", "TE", "K"];
  const years = [2020, 2021, 2022, 2023, 2024];
  const weeks = Array.from({ length: 17 }, (_, i) => i + 1);
  const availableStats = ["CMP", "ATT", "PCT", "YDS", "TD"];
  const [selectedStats] = useState(availableStats);
  const [topN, setTopN] = useState(25);

  // Fetch weekly or season stats
  useEffect(() => {
    const qs = new URLSearchParams({ year, week }).toString();
    const seasonQs = new URLSearchParams({ year }).toString();

    const endpoint =
      view === "weekly"
        ? `http://localhost:8000/api/${position.toLowerCase()}/stats?${qs}`
        : `http://localhost:8000/api/${position.toLowerCase()}/season-stats?${seasonQs}`;

    setLoading(true);
    fetch(endpoint)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then(setRows)
      .catch((e) => setError(e.toString()))
      .finally(() => setLoading(false));
  }, [position, year, week, view]);

  // Determine columns to display
  const allHeaders = rows.length ? Object.keys(rows[0]) : [];
  const hidden = ["week", "year", "G"];
  const trailing = ["FL", "INT", "Sacks", "Score", "Team Name", "ROST"];

  const core =
    view === "season"
      ? ["Player", "Games_Played", "Total_Yards", "Total_TDs", "Total_FPTS", "FPTS_per_game"]
      : ["Rank", "Player", "FPTS"];

  const stats = selectedStats.filter((h) => allHeaders.includes(h));
  const meta = allHeaders.filter(
    (h) => ![...core, ...stats, ...trailing, ...hidden].includes(h)
  );

  const headers = [
    ...core,
    ...stats,
    ...meta,
    ...trailing.filter((h) => allHeaders.includes(h)),
  ];

  // Sorting logic
  const sortedRows = useMemo(() => {
    if (!sortConfig.key) return rows;
    const { key, dir } = sortConfig;
    return [...rows].sort((a, b) => {
      const aNum = +a[key];
      const bNum = +b[key];
      const cmp =
        !isNaN(aNum) && !isNaN(bNum)
          ? aNum - bNum
          : String(a[key]).localeCompare(String(b[key]));
      return dir === "asc" ? cmp : -cmp;
    });
  }, [rows, sortConfig]);

  const toggleSort = (key) => {
    setSortConfig((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "asc" }
    );
  };

  const caret = (key) =>
    sortConfig.key === key ? (sortConfig.dir === "asc" ? " ▲" : " ▼") : "";

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>{position} {view === "weekly" ? "Rankings" : "Season Summary"}</h1>
      </header>

      {/* Filter Bar */}
      <div className="filter-bar">
        <select value={view} onChange={(e) => setView(e.target.value)}>
          <option value="weekly">Weekly Stats</option>
          <option value="season">Season Summary</option>
        </select>

        <select value={position} onChange={(e) => setPosition(e.target.value)}>
          {positionOptions.map((p) => <option key={p}>{p}</option>)}
        </select>

        <select value={year} onChange={(e) => setYear(e.target.value)}>
          {years.map((y) => <option key={y}>{y}</option>)}
        </select>

        {view === "weekly" && (
          <select value={week} onChange={(e) => setWeek(e.target.value)}>
            {weeks.map((w) => <option key={w}>{w}</option>)}
          </select>
        )}

        <select value={topN} onChange={(e) => setTopN(+e.target.value)}>
          {[10, 25, 50, 100, 9999].map((n) => (
            <option key={n} value={n}>{n === 9999 ? "all" : n}</option>
          ))}
        </select>
      </div>

      {error && <p className="error">Error: {error}</p>}
      {loading && <p className="loading">Loading…</p>}

      {!loading && !error && (
        <div className="table-wrap">
          <table className="stats-table">
            <thead>
              <tr>
                {headers.map((h) => (
                  <th key={h} onClick={() => toggleSort(h)}>
                    {h}{caret(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedRows.slice(0, topN).map((row, idx) => (
                <tr key={idx}>
                  {headers.map((h) => (
                    <td key={h}>{row[h]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
