let incidents = [];
let map;
const markersById = {};
let filteredIncidents = [];

// ---------- Utility Functions ----------

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function markerColor(damage, priority) {
    const level = String(priority || "").toUpperCase();
    const damageLevel = String(damage || "").toUpperCase();

    if (level === "IMMEDIATE") return "#991b1b";
    if (level === "HIGH" || damageLevel === "HIGH") return "#d9485f";
    if (level === "MODERATE" || damageLevel === "MODERATE") {
        return "#e8a23c";
    }

    return "#22a77a";
}

function makeMarkerIcon(color) {
    return L.divIcon({
        className: "",
        html: `<div style="
            width:17px;
            height:17px;
            background:${color};
            border:3px solid white;
            border-radius:50%;
            box-shadow:0 1px 7px #172b4d66;
        "></div>`,
        iconSize: [17, 17],
        iconAnchor: [8, 8]
    });
}

// ---------- Map ----------

function initMap() {
    map = L.map("map").setView([16.5062, 80.6480], 12);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);
}

// ---------- Filters ----------

function getFilteredIncidents() {
    const priorityFilter =
        document.getElementById("priority-filter")?.value || "ALL";

    const statusFilter =
        document.getElementById("status-filter")?.value || "ALL";

    return incidents.filter(item => {
        const priority = String(item.priority || "").toUpperCase();

        const priorityMatches =
            priorityFilter === "ALL" || priority === priorityFilter;

        const statusMatches =
            statusFilter === "ALL" || item.status === statusFilter;

        return priorityMatches && statusMatches;
    });
}

function applyDashboardFilters() {
    filteredIncidents = getFilteredIncidents();

    renderPriorityList(filteredIncidents);
    renderTable(filteredIncidents);
    renderMarkers(filteredIncidents);
}

// ---------- Dashboard Statistics ----------

function renderStats(data) {
    document.getElementById("total-sites").textContent = data.length;

    document.getElementById("high-priority").textContent =
        data.filter(item =>
            ["IMMEDIATE", "HIGH"].includes(
                String(item.priority || "").toUpperCase()
            ) || Number(item.score) >= 70
        ).length;

    document.getElementById("pending-sites").textContent =
        data.filter(item =>
            item.status === "Pending inspection"
        ).length;

    document.getElementById("verified-sites").textContent =
        data.filter(item =>
            item.status === "Field verified"
        ).length;
}

// ---------- Priority Summary ----------

function renderPriorityList(data) {
    const container = document.getElementById("priority-list");

    const priorityRank = {
        IMMEDIATE: 4,
        HIGH: 3,
        MODERATE: 2,
        LOW: 1
    };

    const sorted = [...data].sort((a, b) => {
        const rankA =
            priorityRank[String(a.priority || "").toUpperCase()] || 0;
        const rankB =
            priorityRank[String(b.priority || "").toUpperCase()] || 0;

        return rankB - rankA ||
            (Number(b.score) || 0) - (Number(a.score) || 0);
    });

    if (!sorted.length) {
        container.innerHTML =
            '<p class="loading">No matching incidents found.</p>';
        return;
    }

    container.innerHTML = sorted.slice(0, 4).map((item, index) => `
        <div class="priority-item">
            <div class="priority-rank">
                ${String(index + 1).padStart(2, "0")}
            </div>
            <div class="priority-info">
                <strong>${escapeHTML(item.location || "Unknown location")}</strong>
                <small>
                    ${escapeHTML(item.damage || "Unassessed")} estimated damage
                    · ${escapeHTML(item.status || "Pending inspection")}
                </small>
            </div>
            <div class="score">${Number(item.score) || 0}</div>
        </div>
    `).join("");
}

// ---------- Recommended Assistance ----------

function renderRecommendations(item) {
    const recommendations = Array.isArray(item.recommended_assistance)
        ? item.recommended_assistance
        : [];

    if (!recommendations.length) {
        return "<li>No recommendations available</li>";
    }

    return recommendations
        .map(need => `<li>${escapeHTML(need)}</li>`)
        .join("");
}

// ---------- Update Incident Status ----------

async function updateIncidentStatus(incidentId, newStatus) {
    try {
        const response = await fetch(
            `/api/incidents/${encodeURIComponent(incidentId)}/status`,
            {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ status: newStatus })
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Status update failed");
        }

        await loadIncidents();
        alert(`Incident ${incidentId} status updated to ${newStatus}.`);

    } catch (error) {
        console.error("Status update failed:", error);
        alert("Could not update status. Check the Flask terminal.");
        await loadIncidents();
    }
}

// ---------- Inspection Queue ----------

function renderTable(data) {
    const tbody = document.getElementById("incident-table");

    if (!tbody) {
        console.error("Incident table body not found.");
        return;
    }

    if (!data.length) {
        tbody.innerHTML =
            '<tr><td colspan="5">No matching incidents found.</td></tr>';
        return;
    }

    const statuses = [
        "Pending inspection",
        "Field verified",
        "Resolved"
    ];

    tbody.innerHTML = data.map(item => {
        const statusOptions = statuses.map(status => `
            <option value="${status}"
                ${item.status === status ? "selected" : ""}>
                ${status}
            </option>
        `).join("");

        return `
            <tr>
                <td>${escapeHTML(item.id)}</td>
                <td>${escapeHTML(item.location || "Unknown")}</td>
                <td>${escapeHTML(item.damage || "Unassessed")}</td>
                <td>
                    <strong>${Number(item.score) || 0}/100</strong>
                    <br>
                    <small>${escapeHTML(item.priority || "Unclassified")}</small>
                </td>
                <td>
                    <select class="incident-status"
                        data-incident-id="${escapeHTML(item.id)}"
                        aria-label="Update status for ${escapeHTML(item.id)}">
                        ${statusOptions}
                    </select>

                    <details style="margin-top:8px;">
                        <summary style="cursor:pointer;color:#2563eb;">
                            View recommendations
                        </summary>
                        <ul style="padding-left:20px;line-height:1.6;">
                            ${renderRecommendations(item)}
                        </ul>
                        <small>
                            Demo suggestions; verify with field responders.
                        </small>
                    </details>
                </td>
            </tr>
        `;
    }).join("");

    tbody.querySelectorAll(".incident-status").forEach(select => {
        select.addEventListener("change", () => {
            updateIncidentStatus(
                select.dataset.incidentId,
                select.value
            );
        });
    });
}

// ---------- Incident Map Markers ----------

function renderMarkers(data) {
    const currentIds = new Set();
    let firstNewMarkerPosition = null;
    data.forEach(item => {
        if (item.latitude == null || item.longitude == null) {
            return;
        }

        const latitude = Number(item.latitude);
        const longitude = Number(item.longitude);

        if (
            !Number.isFinite(latitude) ||
            !Number.isFinite(longitude) ||
            Math.abs(latitude) > 90 ||
            Math.abs(longitude) > 180
        ) {
            return;
        }

        const id = String(item.id);
        currentIds.add(id);

        const position = [latitude, longitude];
        const color = markerColor(item.damage, item.priority);

        if (markersById[id]) {
            markersById[id].setLatLng(position);
            markersById[id].setIcon(makeMarkerIcon(color));
        } else {
    markersById[id] = L.marker(position, {
        icon: makeMarkerIcon(color)
    }).addTo(map);

    if (firstNewMarkerPosition === null) {
        firstNewMarkerPosition = position;
    }
}

        const popupHTML = `
            <div style="min-width:220px;max-width:300px;">
                <h3>${escapeHTML(item.location || "Unknown location")}</h3>
                <p><strong>Incident:</strong> ${escapeHTML(item.id)}</p>
                <p><strong>Disaster:</strong>
                    ${escapeHTML(item.disaster_type || "Unknown")}</p>
                <p><strong>Priority:</strong>
                    ${escapeHTML(item.priority || "Unclassified")}</p>
                <p><strong>Damage:</strong>
                    ${escapeHTML(item.damage || "Unassessed")}</p>
                <p><strong>Score:</strong> ${Number(item.score) || 0}/100</p>
                <p><strong>People affected:</strong>
                    ${Number(item.people_affected) || 0}</p>
                <p><strong>Status:</strong>
                    ${escapeHTML(item.status || "Pending inspection")}</p>
                <hr>
                <strong>Recommended assistance</strong>
                <ul style="padding-left:20px;line-height:1.5;">
                    ${renderRecommendations(item)}
                </ul>
                <small>${escapeHTML(item.reason || "")}</small>
            </div>
        `;

        markersById[id].bindPopup(popupHTML);
    });

    // Remove markers excluded by the active filters or missing from the API.
    Object.keys(markersById).forEach(id => {
        if (!currentIds.has(id)) {
            map.removeLayer(markersById[id]);
            delete markersById[id];
        }
    });
if (firstNewMarkerPosition !== null) {
    map.invalidateSize();
    map.flyTo(
        firstNewMarkerPosition,
        Math.max(map.getZoom(), 15),
        { duration: 0.8 }
    );
}
};


// ---------- CSV Export ----------

function downloadCsv() {
    const header = [
        "Incident ID",
        "Location",
        "Latitude",
        "Longitude",
        "Disaster Type",
        "Estimated Damage",
        "Priority",
        "Priority Score",
        "People Affected",
        "Recommended Assistance",
        "Status",
        "Reason"
    ];

    const rows = incidents.map(item => [
        item.id,
        item.location,
        item.latitude,
        item.longitude,
        item.disaster_type,
        item.damage,
        item.priority,
        item.score,
        item.people_affected,
        (item.recommended_assistance || []).join("; "),
        item.status,
        item.reason
    ]);

    const escapeCell = value =>
        `"${String(value ?? "").replace(/"/g, '""')}"`;

    const csv = [header, ...rows]
        .map(row => row.map(escapeCell).join(","))
        .join("\r\n");

    const blob = new Blob(["\uFEFF" + csv], {
        type: "text/csv;charset=utf-8;"
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "resqmap-inspection-queue.csv";

    document.body.appendChild(link);
    link.click();
    link.remove();

    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------- Load Incidents ----------


async function loadIncidents() {
    const response = await fetch("/api/incidents");

    if (!response.ok) {
        throw new Error(`Could not load incidents: HTTP ${response.status}`);
    }

    const result = await response.json();

    if (!Array.isArray(result)) {
        throw new Error("The incidents API did not return a list.");
    }

    // Keep the complete list for statistics and exports.
    incidents = result;

    renderStats(incidents);

    // Apply the currently selected filters.
    filteredIncidents = getFilteredIncidents();

    renderPriorityList(filteredIncidents);
    renderTable(filteredIncidents);

    // Update map markers using the filtered records.
    renderMarkers(filteredIncidents);
}


// ---------- Initialize Dashboard ----------

document.addEventListener("DOMContentLoaded", async () => {
    initMap();

    document.getElementById("download-csv")
        ?.addEventListener("click", downloadCsv);

    document.getElementById("priority-filter")
        ?.addEventListener("change", applyDashboardFilters);

    document.getElementById("status-filter")
        ?.addEventListener("change", applyDashboardFilters);

   
   const resetButton = document.getElementById("reset-map-filters");

  if (resetButton) {
    resetButton.addEventListener("click", async function () {
        const priorityFilter = document.getElementById("priority-filter");
        const statusFilter = document.getElementById("status-filter");

        if (priorityFilter) priorityFilter.value = "ALL";
        if (statusFilter) statusFilter.value = "ALL";

        try {
            await loadIncidents();
            applyDashboardFilters();
        } catch (error) {
            console.error("Reset filters failed:", error);
        }
    });
}


    try {
        await loadIncidents();
    } catch (error) {
        console.error("Initial incident loading failed:", error);

        const tbody = document.getElementById("incident-table");
        const priorityList = document.getElementById("priority-list");

        if (tbody) {
            tbody.innerHTML =
                '<tr><td colspan="5">Could not load incidents. Check Flask.</td></tr>';
        }

        if (priorityList) {
            priorityList.innerHTML =
                '<p class="loading">Could not load incident records.</p>';
        }
    }

    // Refresh data every 10 seconds.
    setInterval(async () => {
        try {
            await loadIncidents();
        } catch (error) {
            console.error("Automatic refresh failed:", error);
        }
    }, 10000);
});