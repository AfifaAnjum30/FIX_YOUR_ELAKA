
import os

from django.core.exceptions import ValidationError

ALLOWED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
MAX_IMAGE_SIZE_MB = 5
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024


def validate_image_file(upload):

    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            "Unsupported image type '%(ext)s'. Allowed: JPG, PNG or WEBP.",
            params={"ext": ext or "unknown"},
            code="invalid_image_type",
        )
    if upload.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            "Image is too large (max %(max)s MB).",
            params={"max": MAX_IMAGE_SIZE_MB},
            code="image_too_large",
        )