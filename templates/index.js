const map = L.map('map', {
    center: [52.231, 21.006],
    zoom: 14,
});
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);

const markersGroup = new L.FeatureGroup();
function tagsToHtml(tags) {
    return Object.entries(tags)
        .map(([key, value]) => `<b>${key}</b>=${value}<br/>`)
        .reduce((acc, value) => acc + value, "")
}

function showMarker(latLon, tags) {
    const marker = L.marker(latLon).bindPopup(tagsToHtml(tags))
    if (tags["name"]) marker.bindTooltip(tags["name"], {permanent: true})
    markersGroup.addLayer(marker);
}

features.forEach(feature => {
    showMarker([feature["lat"], feature["lon"]], feature["tags"]);
});
markersGroup.addTo(map);
map.fitBounds(markersGroup.getBounds());

