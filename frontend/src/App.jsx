import React, { useState, useEffect, useMemo } from "react";
import "./App.css";

const API_BASE = "http://localhost:8000/api";

const App = () => {
    const [activeTab, setActiveTab] = useState("qb");
    const [selectedYear, setSelectedYear] = useState("");
    const [availableYears, setAvailableYears] = useState([]);
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [sortConfig, setSortConfig] = useState({ key: "Rank", direction: "ascending" });

    const positions = [
        { id: "qb", label: "Quarterbacks" },
        { id: "rb", label: "Running Backs" },
        { id: "wr", label: "Wide Receivers" },
        { id: "te", label: "Tight Ends" },
        { id: "k", label: "Kickers" },
        { id: "dst", label: "Defense/ST" },
    ];

    const selectedYearRef = React.useRef(selectedYear);
    useEffect(() => {
        selectedYearRef.current = selectedYear;
    }, [selectedYear]);

    // 1. Fetch available seasons for the selected position
    useEffect(() => {
        const fetchSeasons = async () => {
            try {
                const resp = await fetch(`${API_BASE}/rankings/${activeTab}/seasons`);
                if (!resp.ok) throw new Error("Failed to fetch seasons");
                const years = await resp.json();
                setAvailableYears(years);
                
                // Default to the most recent season if not set or not available
                if (years.length > 0) {
                    const latest = years[0].toString();
                    const currentYear = selectedYearRef.current;
                    if (!currentYear || !years.includes(parseInt(currentYear))) {
                        setSelectedYear(latest);
                    }
                }
            } catch (err) {
                console.error("Season fetch error:", err);
                setError("Could not load seasons.");
            }
        };
        fetchSeasons();
    }, [activeTab]);

    // 2. Fetch rankings based on position and year
    useEffect(() => {
        const fetchRankings = async () => {
            if (!selectedYear) return;
            setLoading(true);
            setError(null);
            try {
                const resp = await fetch(`${API_BASE}/rankings/${activeTab}?year=${selectedYear}`);
                if (!resp.ok) throw new Error("Failed to fetch rankings");
                const jsonData = await resp.json();
                setData(jsonData);
            } catch (err) {
                console.error("Ranking fetch error:", err);
                setError("Failed to load rankings data.");
                setData([]);
            } finally {
                setLoading(false);
            }
        };
        fetchRankings();
    }, [activeTab, selectedYear]);

    // 3. Sorting logic
    const handleSort = (key) => {
        let direction = "ascending";
        if (sortConfig.key === key && sortConfig.direction === "ascending") {
            direction = "descending";
        }
        setSortConfig({ key, direction });
    };

    const sortedData = useMemo(() => {
        if (!sortConfig.key) return data;
        return [...data].sort((a, b) => {
            const aVal = a[sortConfig.key];
            const bVal = b[sortConfig.key];
            
            if (aVal === bVal) return 0;
            
            const isNumeric = !isNaN(parseFloat(aVal)) && isFinite(aVal);
            if (isNumeric) {
                return sortConfig.direction === "ascending" ? aVal - bVal : bVal - aVal;
            }
            
            return sortConfig.direction === "ascending" 
                ? String(aVal).localeCompare(String(bVal))
                : String(bVal).localeCompare(String(aVal));
        });
    }, [data, sortConfig]);

    // 4. Filtering logic
    const filteredData = searchQuery
        ? sortedData.filter(item => 
            item.Player?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            item.Team?.toLowerCase().includes(searchQuery.toLowerCase())
          )
        : sortedData;

    // Helper to format column headers
    const formatHeader = (key) => {
        const mapping = {
            "FPTS_PPR": "Fantasy Points (PPR)",
            "FPTS": "Fantasy Points",
            "AVG": "Avg / Game",
        };
        return mapping[key] || key;
    };

    return (
        <div className="app-shell">
            <header className="premium-header">
                <div className="brand">
                    <h1 className="logo-text">NFL<span>Analyzer</span></h1>
                    <p className="tagline">Next-Gen Performance Analytics</p>
                </div>
                
                <nav className="tab-navigation">
                    {positions.map(pos => (
                        <button 
                            key={pos.id}
                            className={`tab-link ${activeTab === pos.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(pos.id)}
                        >
                            {pos.label}
                        </button>
                    ))}
                </nav>
            </header>

            <main className="main-content">
                <section className="control-deck">
                    <div className="control-group">
                        <label>Season</label>
                        <select 
                            value={selectedYear} 
                            onChange={(e) => setSelectedYear(e.target.value)}
                            className="glass-select"
                        >
                            {availableYears.map(y => (
                                <option key={y} value={y}>{y}</option>
                            ))}
                        </select>
                    </div>

                    <div className="control-group search">
                        <input 
                            type="text" 
                            placeholder="Search player or team..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="glass-input"
                        />
                    </div>
                </section>

                {error && <div className="error-toast">{error}</div>}

                <div className="data-surface">
                    {loading ? (
                        <div className="shimmer-loader">Analyzing Season Data...</div>
                    ) : filteredData.length > 0 ? (
                        <div className="table-overflow">
                            <table className="premium-table">
                                <thead>
                                    <tr>
                                        {Object.keys(data[0] || {}).map(key => (
                                            <th key={key} onClick={() => handleSort(key)} className="sortable">
                                                {formatHeader(key)}
                                                {sortConfig.key === key && (
                                                    <span className="sort-indicator">
                                                        {sortConfig.direction === "ascending" ? "↑" : "↓"}
                                                    </span>
                                                )}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredData.map((row, idx) => (
                                        <tr key={idx} className="table-row">
                                            {Object.keys(data[0]).map(key => (
                                                <td key={key} data-label={formatHeader(key)}>
                                                    {row[key]}
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="empty-state">
                            <p>No data found for the selected criteria.</p>
                        </div>
                    )}
                </div>
            </main>

            <footer className="simple-footer">
                <p>&copy; 2026 NFL Stats Analyzer. All rights reserved.</p>
            </footer>
        </div>
    );
};

export default App;
