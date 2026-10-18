document.addEventListener('DOMContentLoaded', async () => {
  const el = document.getElementById('community-map');
  if (!el || typeof L === 'undefined') return;
  const map = L.map(el).setView([23.8103, 90.4125], 11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors', maxZoom: 19
  }).addTo(map);
  const feedback = document.getElementById('map-feedback');
  const params = new URLSearchParams(new FormData(document.getElementById('map-filters')));
  try {
    const response = await fetch(`${el.dataset.endpoint}?${params}`);
    if (!response.ok) throw new Error('Unable to load map data');
    const data = await response.json();
    const layer = L.geoJSON(data, {
      onEachFeature: (feature, marker) => {
        const p = feature.properties;
        // Use DOM textContent rather than interpolating user input into HTML.
        const box = document.createElement('div');
        const title = document.createElement('strong'); title.textContent = p.title;
        const info = document.createElement('div'); info.textContent = `${p.area} · ${p.category} · ${p.status}`;
        box.append(title, info); marker.bindPopup(box);
      }
    }).addTo(map);
    if (layer.getLayers().length) map.fitBounds(layer.getBounds(), {padding: [30,30], maxZoom: 15});
    feedback.textContent = `${layer.getLayers().length} verified public report(s) displayed.`;
  } catch (err) { feedback.textContent = 'Could not load reports. Please try again.'; }
});
