
document.addEventListener('DOMContentLoaded', () => {
  const mapEl = document.getElementById('picker-map');
  const latInput = document.getElementById('id_latitude');
  const lngInput = document.getElementById('id_longitude');
  if (!mapEl || !latInput || !lngInput || typeof L === 'undefined') return;

  const DHAKA = [23.8103, 90.4125];
  const startLat = parseFloat(latInput.value);
  const startLng = parseFloat(lngInput.value);
  const hasStart = !isNaN(startLat) && !isNaN(startLng);

  const map = L.map(mapEl).setView(hasStart ? [startLat, startLng] : DHAKA, hasStart ? 16 : 12);
  L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    { maxZoom: 19, attribution: 'Tiles &copy; Esri' }
  ).addTo(map);

  const locationTextInput = document.getElementById("id_location_text");

  async function updateLocationText(lat, lng) {
      if (!locationTextInput) return;

      locationTextInput.value = "Finding location...";

      try {
          const url = new URL(
              "https://nominatim.openstreetmap.org/reverse"
          );

          url.searchParams.set("format", "jsonv2");
          url.searchParams.set("lat", lat);
          url.searchParams.set("lon", lng);
          url.searchParams.set("zoom", "18");
          url.searchParams.set("addressdetails", "1");

          const response = await fetch(url);

          if (!response.ok) {
              throw new Error("Location lookup failed");
          }

          const data = await response.json();

          locationTextInput.value =
              data.display_name ||
              `${lat.toFixed(6)}, ${lng.toFixed(6)}`;

      } catch (error) {
          locationTextInput.value =
            ` ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
      }
  }

  let marker = hasStart ? L.marker([startLat, startLng]).addTo(map) : null;

  function setPoint(lat, lng, pan) {
    latInput.value = lat.toFixed(6);
    lngInput.value = lng.toFixed(6);
    if (marker) marker.setLatLng([lat, lng]); else marker = L.marker([lat, lng]).addTo(map);
    if (pan) map.setView([lat, lng], 16);
    updateLocationText(lat, lng);
  }
  // updateLocationText(lat, lng);

  map.on('click', (e) => setPoint(e.latlng.lat, e.latlng.lng, false));


  function syncFromInputs() {
    const lat = parseFloat(latInput.value), lng = parseFloat(lngInput.value);
    if (!isNaN(lat) && !isNaN(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
      if (marker) marker.setLatLng([lat, lng]); else marker = L.marker([lat, lng]).addTo(map);
      map.setView([lat, lng], Math.max(map.getZoom(), 14));
    }
  }
  latInput.addEventListener('change', syncFromInputs);
  lngInput.addEventListener('change', syncFromInputs);

  const btn = document.getElementById('use-my-location');
  if (btn) btn.addEventListener('click', () => {
    if (!navigator.geolocation) { alert('Geolocation is not supported by your browser.'); return; }
    navigator.geolocation.getCurrentPosition(
      (pos) => setPoint(pos.coords.latitude, pos.coords.longitude, true),
      () => alert('Could not get your location. Please click the map instead.')
    );
  });
});