const map = L.map("map", {
  zoomControl: true,
  attributionControl: true,
}).setView([1.3521, 103.8198], 11);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

let heatLayer = null;
const markerLayer = L.layerGroup().addTo(map);

function setMessage(text, isError = false) {
  const messageNode = document.getElementById("message");
  messageNode.textContent = text || "";
  messageNode.style.color = isError ? "#982f15" : "#35536a";
}

function updateStats(payload) {
  document.getElementById("case-count").textContent = payload.case_count ?? "-";
  document.getElementById("point-count").textContent = payload.point_count ?? "-";
  document.getElementById("dataset-name").textContent = payload.data_file ?? "-";

  if (payload.year_bounds) {
    const yearFromInput = document.getElementById("year-from");
    const yearToInput = document.getElementById("year-to");
    if (!yearFromInput.value) {
      yearFromInput.placeholder = payload.year_bounds.min;
    }
    if (!yearToInput.value) {
      yearToInput.placeholder = payload.year_bounds.max;
    }
  }
}

function renderHeatmap(points) {
  if (heatLayer) {
    map.removeLayer(heatLayer);
  }
  markerLayer.clearLayers();

  const heatData = points.map((point) => [
    point.latitude,
    point.longitude,
    Math.max(0.1, point.weight),
  ]);

  heatLayer = L.heatLayer(heatData, {
    radius: 27,
    blur: 21,
    maxZoom: 13,
    minOpacity: 0.35,
    gradient: {
      0.25: "#2a9d8f",
      0.55: "#f4a261",
      0.85: "#e76f51",
      1.0: "#c4380f",
    },
  }).addTo(map);

  points.slice(0, 18).forEach((point) => {
    const marker = L.circleMarker([point.latitude, point.longitude], {
      radius: 4 + Math.min(point.weight, 2.8) * 2.5,
      color: "#1f4259",
      weight: 1,
      fillColor: "#ff8f55",
      fillOpacity: 0.7,
    });
    marker.bindPopup(
      `<strong>${point.location}</strong><br/>Weight: ${point.weight.toFixed(2)}<br/>Cases: ${Math.round(
        point.case_count
      )}`
    );
    marker.addTo(markerLayer);
  });

  if (points.length > 0) {
    const bounds = L.latLngBounds(points.map((point) => [point.latitude, point.longitude]));
    map.fitBounds(bounds.pad(0.22), { animate: true, duration: 0.6 });
  } else {
    map.setView([1.3521, 103.8198], 11);
  }
}

async function loadHeatmap() {
  const yearFrom = document.getElementById("year-from").value.trim();
  const yearTo = document.getElementById("year-to").value.trim();
  const minWeight = document.getElementById("min-weight").value.trim();

  const params = new URLSearchParams();
  if (yearFrom) params.set("year_from", yearFrom);
  if (yearTo) params.set("year_to", yearTo);
  if (minWeight) params.set("min_weight", minWeight);

  setMessage("Loading heatmap data...");
  try {
    const response = await fetch(`/api/heatmap?${params.toString()}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Heatmap request failed.");
    }
    updateStats(payload);
    renderHeatmap(payload.points || []);
    setMessage(
      `Loaded ${payload.point_count} hotspots from ${payload.case_count} cases.`,
      false
    );
  } catch (error) {
    setMessage(error.message, true);
  }
}

document.getElementById("refresh-button").addEventListener("click", () => {
  loadHeatmap();
});

loadHeatmap();
