
document.addEventListener("DOMContentLoaded", () => {
  const locationInput = document.getElementById(
    "id_location_text"
  );

  const areaSelect = document.getElementById("id_area");

  if (!locationInput || !areaSelect) return;

  function suggestArea() {
    const location = locationInput.value
      .trim()
      .toLowerCase();

    if (!location) return;

    const options = Array.from(areaSelect.options)
      .filter(option => option.value);

    // Match a registered area name in the entered location.
    const matches = options.filter(option => {
      const areaName = option.textContent
        .trim()
        .toLowerCase();

      return areaName && location.includes(areaName);
    });

    // Only select automatically when there is one match.
    if (matches.length === 1) {
      areaSelect.value = matches[0].value;

      areaSelect.dispatchEvent(
        new Event("change", { bubbles: true })
      );
    }
  }

  locationInput.addEventListener("input", suggestArea);
  locationInput.addEventListener("blur", suggestArea);
});
