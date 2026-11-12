"""
Cloudinary storage backend.
Django ke ImageField/FileField isse seedha kaam karte hain (upload, url, delete).
"""
import logging
import os
import uuid

import cloudinary.uploader
import cloudinary.utils
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)


@deconstructible
class CloudinaryMediaStorage(Storage):
    def get_available_name(self, name, max_length=None):
        """
        Original filename ki jagah random uuid naam: collision nahi hoga
        aur DB ke 100-char limit mein hamesha fit hoga.
        """
        name = str(name).replace("\\", "/")
        folder, _, filename = name.rpartition("/")
        extension = os.path.splitext(filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex}{extension}"
        return f"{folder}/{unique_name}" if folder else unique_name

    def _save(self, name, content):
        if hasattr(content, "seek"):
            content.seek(0)

        public_id = os.path.splitext(name)[0]
        result = cloudinary.uploader.upload(
            content.read(),
            public_id=public_id,
            resource_type="image",
            overwrite=False,
            unique_filename=False,
            use_filename=False,
        )
        # DB mein public_id + extension store hoga (e.g. properties/2026/11/abc123.jpg)
        return f"{result['public_id']}.{result['format']}"

    def url(self, name):
        return cloudinary.utils.cloudinary_url(name, secure=True)[0]

    def delete(self, name):
        public_id = os.path.splitext(name)[0]
        try:
            cloudinary.uploader.destroy(public_id, invalidate=True)
        except Exception:
            logger.exception("Cloudinary delete failed for %s", name)

    def exists(self, name):
        # Naam uuid se unique hai, isliye collision check ki zaroorat nahi
        return False

    def _open(self, name, mode="rb"):
        raise NotImplementedError("Cloudinary files remote hain, direct open supported nahi hai.")

    def size(self, name):
        raise NotImplementedError("Size Cloudinary se fetch nahi kiya jata.")