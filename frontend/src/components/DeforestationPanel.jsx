import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./DeforestationPanel.css";

const API = "http://127.0.0.1:8000";

const STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
];

function ChangeView({ center, zoom }) {
    const map = useMap();
    map.setView(center, zoom);
    return null;
}

const STATE_DATA = {
    "Andhra Pradesh": {
        causes: ["Podu (shifting) cultivation", "Illegal logging of red sanders", "Mining and quarrying"],
        theory: "Deforestation in Andhra Pradesh is complex, primarily driven by traditional 'Podu' (slash-and-burn) agriculture in tribal belts and unchecked illegal logging in the Seshachalam hills.",
        solution: "Promote settled agriculture through financial incentives, strictly enforce anti-smuggling laws using satellite monitoring, and engage local tribes in joint forest management.",
        solutionsList: ["Promote settled agriculture alternatives", "Intensify anti-smuggling operations using drones", "Joint Forest Management (JFM) with tribals"]
    },
    "Arunachal Pradesh": {
        causes: ["Jhum cultivation", "Hydropower projects", "Rampant timber extraction"],
        theory: "Known for its dense canopy, Arunachal Pradesh faces severe fragmentation due to large-scale infrastructure projects (especially dams) and historical reliance on shifting agriculture (Jhum).",
        solution: "Implementing sustainable terrace farming methods and ensuring rigorous Environmental Impact Assessments (EIA) for dam constructions are critical to preserving this biodiversity hotspot.",
        solutionsList: ["Transition from Jhum to terrace farming", "Strict enforcement of EIAs for infrastructure", "Promotion of eco-tourism"]
    },
    "Assam": {
        causes: ["Encroachment for settlements", "Tea estate expansion", "Illegal logging in reserves"],
        theory: "Assam's forests are under immense pressure from population expansion leading to encroachment, as well as the historical and ongoing clearing of land for commercial tea plantations.",
        solution: "Strengthening eviction protocols in reserved forests, creating buffer zones around wildlife sanctuaries, and promoting shade-grown sustainable tea farming.",
        solutionsList: ["Clear demarcation and protection of forest boundaries", "Encourage shade-grown sustainable tea practices", "Community-led afforestation in degraded areas"]
    },
    "Chhattisgarh": {
        causes: ["Coal and bauxite mining", "Industrial expansion", "Forest fires (LFPs)"],
        theory: "The mineral-rich state of Chhattisgarh loses significant forest cover to massive open-cast mining operations and subsequent industrial infrastructure, exacerbated by recurring forest fires.",
        solution: "Mandatory, rigorous mine reclamation protocols, deployment of early-warning fire detection systems, and transition to sustainable mining practices.",
        solutionsList: ["Mandatory ecological restoration of mined areas", "Early-warning thermal anomaly detection for fires", "Stricter oversight on industrial land acquisition"]
    },
    "Madhya Pradesh": {
        causes: ["Diamond and coal mining", "Agricultural expansion", "Firewood collection"],
        theory: "Possessing the largest forest cover in India, MP faces constant degradation from both large-scale mining operations and the heavy reliance of rural populations on forests for fuelwood.",
        solution: "Providing subsidized clean cooking fuel (LPG) to reduce firewood dependency, alongside strict ecological restoration mandates for mining corporations.",
        solutionsList: ["Expand subsidized clean fuel (Ujjwala Yojana) reach", "Corporate accountability for mine reclamation", "Strengthen wildlife corridor protections"]
    },
    "Maharashtra": {
        causes: ["Rapid urbanization", "Linear infrastructure (highways/rail)", "Agricultural encroachment"],
        theory: "The push for rapid economic development in Maharashtra has led to the fragmentation of the Western Ghats through highways, railways, and expanding urban sprawl.",
        solution: "Implementing green infrastructure (wildlife overpasses/underpasses), strict zoning laws to prevent urban sprawl into the Ghats, and massive urban afforestation.",
        solutionsList: ["Mandatory wildlife corridors for new highways", "Strict enforcement of eco-sensitive zones", "Urban micro-forest initiatives (Miyawaki method)"]
    },
    "Mizoram": {
        causes: ["Extensive Jhum (shifting) cultivation", "Bamboo extraction", "Road construction"],
        theory: "In Mizoram, the primary driver of forest loss is the deeply ingrained cultural practice of Jhum cultivation, where land is cleared, burned, and abandoned, leaving severe scars on the landscape.",
        solution: "Transitioning communities from shifting cultivation to lucrative horticulture (like dragon fruit) and sustainable bamboo harvesting.",
        solutionsList: ["Subsidize transition to horticulture crops", "Regulate and certify sustainable bamboo harvesting", "Enhance soil conservation techniques"]
    },
    "Odisha": {
        causes: ["Iron ore and coal mining", "Industrialization", "Podu cultivation"],
        theory: "Odisha struggles to balance industrial growth with conservation, losing dense forests to extensive iron ore mining and steel plant expansions, alongside localized shifting agriculture.",
        solution: "Enforcing strict compensatory afforestation, utilizing mined-out lands for solar installations rather than clearing new forests, and supporting tribal livelihoods.",
        solutionsList: ["Transparent tracking of compensatory afforestation funds", "Repurpose exhausted mines for renewable energy", "Community forest rights recognition"]
    },
    "Kerala": {
        causes: ["Monoculture plantations (Rubber/Teak)", "Tourism infrastructure", "Encroachment"],
        theory: "The delicate ecosystem of the Western Ghats in Kerala is threatened by the conversion of natural forests into commercial monoculture plantations and unregulated tourism development.",
        solution: "Banning further conversion of natural forests, implementing strict eco-tourism guidelines, and restoring degraded plantation lands back to native biodiversity.",
        solutionsList: ["Phase out harmful monoculture plantations", "Certify eco-tourism operators", "Restore riparian (riverbank) forests"]
    },
    "National": {
        causes: ["Agricultural clearing and slash-and-burn practices", "Infrastructure development (roads, dams)", "Illegal logging and timber extraction"],
        theory: "Large-scale forest removal on a national level severely hampers carbon sequestration capabilities. This massive ecological shift accelerates climate change, destroys critical biodiversity habitats, and threatens indigenous communities reliant on forest ecosystems.",
        solution: "Reversing this trend requires a multi-faceted approach combining strict policy enforcement with advanced monitoring technology.",
        solutionsList: ["Afforestation: Aggressive replanting of native tree species", "Agroforestry: Integrating trees into farming systems", "Monitoring: Continuous satellite tracking to catch illegal clearings", "Policy: Stricter penalties for unauthorized logging and land grabs"]
    }
};

export default function DeforestationPanel() {
    const [events, setEvents] = useState([]);
    const [report, setReport] = useState(null);
    const [selectedState, setSelectedState] = useState(null);
    const [mapCenter, setMapCenter] = useState([20.5937, 78.9629]);
    const [mapZoom, setMapZoom] = useState(5);

    useEffect(() => {
        fetch(`${API}/deforestation-events`)
            .then(res => res.json())
            .then(data => setEvents(data))
            .catch(err => console.error(err));

        fetch(`${API}/deforestation-state-report`)
            .then(res => res.json())
            .then(data => setReport(data))
            .catch(err => console.error(err));
    }, []);

    const handleMarkerClick = (evt) => {
        setSelectedState(evt.state);
        setMapCenter([evt.lat, evt.lon]);
        setMapZoom(7);
    };

    const handleStateClick = (stateName) => {
        setSelectedState(stateName);
        // Find an event in that state to center map, or use default
        const stateEvents = events.filter(e => e.state === stateName);
        if (stateEvents.length > 0) {
            setMapCenter([stateEvents[0].lat, stateEvents[0].lon]);
            setMapZoom(6);
        } else {
            setMapCenter([20.5937, 78.9629]);
            setMapZoom(5);
        }
    };

    const stateDetails = report?.state_reports?.find(r => r.state === selectedState);
    const affectedStatesList = report?.state_reports?.map(r => r.state) || [];

    const displayData = selectedState && STATE_DATA[selectedState] ? STATE_DATA[selectedState] : (selectedState ? {
        causes: ["Rapid urbanization", "Agricultural expansion", "Infrastructure projects"],
        theory: `Deforestation in ${selectedState} is currently characterized by land-use changes favoring economic development, agriculture, and expanding infrastructure networks over conservation.`,
        solution: `Immediate localized interventions are required in ${selectedState}, focusing on sustainable land-use planning and expanding protected area networks.`,
        solutionsList: ["Implement sustainable zoning laws", "Increase protected area coverage", "Community-based conservation awareness"]
    } : STATE_DATA["National"]);

    return (
        <div className="deforestation-dashboard-wrapper">
            {/* SIDEBAR FOR STATES */}
            <div className="dashboard-sidebar">
                <div className="sidebar-header">
                    <h2>Forest Monitor</h2>
                    <p>Deforestation Tracking</p>
                </div>
                <div className="sidebar-list">
                    <button
                        className={`state-btn ${!selectedState ? 'active' : ''}`}
                        onClick={() => { setSelectedState(null); setMapCenter([20.5937, 78.9629]); setMapZoom(5); }}
                    >
                        <span className="state-icon">🇮🇳</span>
                        National Overview
                    </button>
                    {STATES.map(state => {
                        const isAffected = affectedStatesList.includes(state);
                        return (
                            <button
                                key={state}
                                className={`state-btn ${selectedState === state ? 'active' : ''}`}
                                onClick={() => handleStateClick(state)}
                            >
                                <span className="state-icon">{isAffected ? '⚠️' : '🌲'}</span>
                                {state}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* MAIN CONTENT AREA */}
            <div className="dashboard-main-content">
                <div className="view-header flex-header">
                    <div className="title-group">
                        <span className="title-super">Satellite Analysis</span>
                        <h1>{selectedState ? `${selectedState} Deforestation Data` : 'Global Deforestation Scanner'}</h1>
                    </div>
                </div>

                <div className="dashboard-scrollable-content">
                    {/* THEORY AND SOLUTIONS SECTION */}
                    <div className="chart-container" style={{ padding: "30px", background: "rgba(15, 23, 42, 0.8)", borderLeft: "4px solid #3b82f6" }}>
                        <h2 style={{ color: "#60a5fa", marginTop: 0 }}>
                            {selectedState ? `Understanding Deforestation in ${selectedState}` : "Global Impact of Deforestation"}
                        </h2>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: '20px' }}>
                            <div>
                                <h3 style={{ color: "#e2e8f0", fontSize: "1.1rem", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "10px" }}>
                                    <span style={{ marginRight: '8px' }}>📖</span> Core Theory & Causes
                                </h3>
                                <p style={{ color: "#cbd5e1", lineHeight: "1.6", fontSize: "0.95rem" }}>
                                    {displayData.theory}
                                </p>
                                <ul style={{ color: "#94a3b8", lineHeight: "1.6", fontSize: "0.9rem", paddingLeft: "20px" }}>
                                    {displayData.causes.map((cause, idx) => (
                                        <li key={idx}>{cause}</li>
                                    ))}
                                </ul>
                            </div>

                            <div>
                                <h3 style={{ color: "#86efac", fontSize: "1.1rem", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "10px" }}>
                                    <span style={{ marginRight: '8px' }}>🌱</span> Actionable Solutions
                                </h3>
                                <p style={{ color: "#cbd5e1", lineHeight: "1.6", fontSize: "0.95rem" }}>
                                    {displayData.solution}
                                </p>
                                <ul style={{ color: "#94a3b8", lineHeight: "1.6", fontSize: "0.9rem", paddingLeft: "20px" }}>
                                    {displayData.solutionsList.map((sol, idx) => (
                                        <li key={idx}>{sol}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>

                    {/* DATA VISUALIZATION SECTION */}
                    {selectedState ? (
                        <>
                            {stateDetails ? (
                                <>
                                    <div className="kpi-cards">
                                        <div className="kpi-card">
                                            <div className="kpi-icon">🔥</div>
                                            <div className="kpi-details">
                                                <span>Total Area Lost</span>
                                                <strong>{stateDetails.total_area_lost} <small>sq km</small></strong>
                                            </div>
                                        </div>
                                        <div className="kpi-card alert-kpi">
                                            <div className="kpi-icon">📍</div>
                                            <div className="kpi-details">
                                                <span>Hotspots</span>
                                                <strong>{stateDetails.hotspot_count} <small>locations</small></strong>
                                            </div>
                                        </div>
                                        <div className="kpi-card">
                                            <div className="kpi-icon">📉</div>
                                            <div className="kpi-details">
                                                <span>Affected Districts</span>
                                                <strong>{stateDetails.districts_count} <small>districts</small></strong>
                                            </div>
                                        </div>
                                    </div>

                                    {stateDetails.future_prediction && (
                                        <div className="state-ai-analysis">
                                            <div className="ai-report-card">
                                                <div className="ai-report-header">
                                                    <span className="header-icon">🤖</span>
                                                    <div className="header-titles">
                                                        <h3>AI Impact Prediction</h3>
                                                        <p>Based on deep learning analysis of satellite data</p>
                                                    </div>
                                                    <div className={`risk-shield risk-${stateDetails.future_prediction.future_risk_level?.toLowerCase() || 'moderate'}`}>
                                                        {stateDetails.future_prediction.future_risk_level}
                                                        <span>RISK BY 2050</span>
                                                    </div>
                                                </div>
                                                <div className="ai-insight-text">
                                                    <p className="ai-insight-warning">{stateDetails.future_prediction.ai_warning || "System monitoring ecological impact."}</p>
                                                </div>
                                            </div>

                                            <div className="event-history-list">
                                                <h3>Recent Events</h3>
                                                <div className="event-list-grid">
                                                    {stateDetails.events.map(e => (
                                                        <div key={e.id} className="history-event-card">
                                                            <div className="event-dist">
                                                                <span>{e.district}</span>
                                                                <span className={`risk-badge risk-${(e.risk || 'low').toLowerCase()}`}>{e.risk}</span>
                                                            </div>
                                                            <div className="event-metrics">
                                                                <span>Area: {e.area} sq km</span>
                                                                {e.ndvi_shift !== undefined && e.ndvi_shift !== null && (
                                                                    <span style={{display: 'block', fontSize: '12px', color: '#f87171', marginTop: '4px'}}>
                                                                        NDVI Shift: {parseFloat(e.ndvi_shift).toFixed(3)}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            {e.t1_ndvi_url && e.t2_ndvi_url && (
                                                                <div className="ndvi-images" style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                                                                    <div style={{ flex: 1, textAlign: 'center' }}>
                                                                        <span style={{ fontSize: '10px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>T1 (Before)</span>
                                                                        <img src={e.t1_ndvi_url} alt="T1 NDVI" style={{ width: '100%', borderRadius: '4px', border: '1px solid #334155' }} />
                                                                    </div>
                                                                    <div style={{ flex: 1, textAlign: 'center' }}>
                                                                        <span style={{ fontSize: '10px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>T2 (Current)</span>
                                                                        <img src={e.t2_ndvi_url} alt="T2 NDVI" style={{ width: '100%', borderRadius: '4px', border: '1px solid #334155' }} />
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <div className="chart-container">
                                    <p className="no-data-msg">No deforestation data analytics available for {selectedState}.</p>
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="chart-container">
                            <h3>National Overview summary</h3>
                            {report ? (
                                <div className="kpi-cards">
                                    <div className="kpi-card">
                                        <div className="kpi-icon">🇮🇳</div>
                                        <div className="kpi-details">
                                            <span>States Affected</span>
                                            <strong>{report.total_states_affected}</strong>
                                        </div>
                                    </div>
                                    <div className="kpi-card alert-kpi">
                                        <div className="kpi-icon">⚠️</div>
                                        <div className="kpi-details">
                                            <span>National Area Lost</span>
                                            <strong>{report.total_national_area_lost} <small>sq km</small></strong>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <p className="no-data-msg">Loading national statistics...</p>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
