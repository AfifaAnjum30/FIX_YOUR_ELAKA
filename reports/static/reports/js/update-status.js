document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.querySelector('#status-upload-box input[type="file"]');
  const preview = document.getElementById('status-image-preview');
  const filename = document.getElementById('status-file-name');
  let previewUrl = null;
  if (fileInput && preview && filename) {
    fileInput.addEventListener('change', () => {
      if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
      const file = fileInput.files && fileInput.files[0];
      filename.textContent = file ? file.name : '';
      preview.hidden = true;
      preview.removeAttribute('src');
      if (file && file.type.startsWith('image/')) {
        previewUrl = URL.createObjectURL(file);
        preview.src = previewUrl;
        preview.hidden = false;
      }
    });
  }
  const form = document.getElementById('status-update-form');
  const submit = document.getElementById('status-submit');
  if (form && submit) {
    form.addEventListener('submit', () => {
      submit.disabled = true;
      submit.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Updating...';
    });
  }
});
