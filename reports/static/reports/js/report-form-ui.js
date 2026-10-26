
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("report-form");

    if (!form) return;

    // Existing Django form fields
    const category = document.getElementById("id_category");
    const photoInput = document.getElementById("id_before_image");

    // UI elements
    const safetyNotice = document.getElementById("safety-notice");
    const uploadBox = document.getElementById("photo-upload");
    const uploadFilename = document.getElementById("upload-filename");
    const preview = document.getElementById("photo-preview");
    const previewImage = document.getElementById("photo-preview-image");
    const removePhoto = document.getElementById("remove-photo");
    const submitButton = document.getElementById("submit-report");
    const submitLabel = document.getElementById("submit-label");

    let previewURL = null;

    // 1. Safety Concern privacy notice
    function updateSafetyNotice() {
        if (!category || !safetyNotice) return;

        const selectedText =
            category.options[category.selectedIndex]?.text || "";

        const isSafety =
            selectedText.trim().toLowerCase() === "safety concern";

        safetyNotice.hidden = !isSafety;
    }

    if (category) {
        category.addEventListener("change", updateSafetyNotice);
        updateSafetyNotice();
    }

    // 2. Clickable upload area
    if (uploadBox && photoInput) {
        uploadBox.setAttribute("role", "button");
        uploadBox.setAttribute("tabindex", "0");

        uploadBox.addEventListener("click", function () {
            photoInput.click();
        });

        uploadBox.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                photoInput.click();
            }
        });
    }

    // 3. Image preview
    function clearPreview() {
        if (previewURL) {
            URL.revokeObjectURL(previewURL);
            previewURL = null;
        }

        if (previewImage) {
            previewImage.removeAttribute("src");
        }

        if (preview) preview.hidden = true;
        if (uploadFilename) uploadFilename.textContent = "";
    }

    if (photoInput) {
        photoInput.addEventListener("change", function () {
            clearPreview();

            const file = photoInput.files?.[0];
            if (!file) return;

            if (uploadFilename) {
                uploadFilename.textContent = file.name;
            }

            if (!file.type.startsWith("image/")) {
                return;
            }

            previewURL = URL.createObjectURL(file);

            if (previewImage) previewImage.src = previewURL;
            if (preview) preview.hidden = false;
        });
    }

    // 4. Remove selected photo
    if (removePhoto && photoInput) {
        removePhoto.addEventListener("click", function () {
            photoInput.value = "";
            clearPreview();
        });
    }

    // 5. Prevent accidental double submission
    form.addEventListener("submit", function () {
        if (submitButton) {
            submitButton.disabled = true;
        }

        if (submitLabel) {
            submitLabel.textContent = "Submitting...";
        }
    });

    window.addEventListener("pagehide", function () {
        if (previewURL) {
            URL.revokeObjectURL(previewURL);
        }
    });
});
