"""
Screenshot storage service supporting both Firebase Storage and local filesystem.

Handles saving, retrieving, and cleaning up simulation screenshots.
Uses Firebase Storage in production, local filesystem in development.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from pathlib import Path
import base64

from firebase_admin import storage

logger = logging.getLogger(__name__)

# Configuration
STORAGE_MODE = os.getenv("SCREENSHOT_STORAGE", "local")  # "firebase" or "local"
LOCAL_STORAGE_ROOT = os.getenv("LOCAL_SCREENSHOT_PATH", "../../screenshots/simulations")
FIREBASE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "iflow-robot.appspot.com")
SCREENSHOT_RETENTION_DAYS = int(os.getenv("SCREENSHOT_RETENTION_DAYS", "7"))


class ScreenshotStorage:
    """Handles screenshot storage with support for Firebase and local filesystem."""

    def __init__(self, mode: Optional[str] = None):
        """
        Initialize screenshot storage.

        Args:
            mode: "firebase" or "local". If None, uses SCREENSHOT_STORAGE env var.
        """
        self.mode = mode or STORAGE_MODE
        logger.info(f"Screenshot storage initialized in {self.mode} mode")

        if self.mode == "local":
            # Ensure local storage directory exists
            self.local_root = Path(LOCAL_STORAGE_ROOT)
            self.local_root.mkdir(parents=True, exist_ok=True)
            logger.info(f"Local storage root: {self.local_root.absolute()}")
        elif self.mode == "firebase":
            try:
                self.bucket = storage.bucket(FIREBASE_BUCKET)
                logger.info(f"Firebase storage bucket: {FIREBASE_BUCKET}")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase storage: {e}")
                logger.warning("Falling back to local storage")
                self.mode = "local"
                self.local_root = Path(LOCAL_STORAGE_ROOT)
                self.local_root.mkdir(parents=True, exist_ok=True)

    def save_screenshot(
        self,
        uid: str,
        timestamp: str,
        step_number: int,
        screenshot_data: bytes,
        step_name: Optional[str] = None
    ) -> str:
        """
        Save a screenshot and return its URL or path.

        Args:
            uid: User ID
            timestamp: ISO timestamp for this simulation run
            step_number: Sequential step number (0-indexed)
            screenshot_data: Raw PNG bytes
            step_name: Optional descriptive name for the step

        Returns:
            URL (for Firebase) or relative path (for local)
        """
        # Generate filename
        if step_name:
            # Sanitize step name for filename
            safe_step_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in step_name)
            filename = f"step_{step_number:02d}_{safe_step_name}.png"
        else:
            filename = f"step_{step_number:02d}.png"

        # Build path
        path = f"users/{uid}/simulations/{timestamp}/{filename}"

        if self.mode == "firebase":
            return self._save_to_firebase(path, screenshot_data)
        else:
            return self._save_to_local(path, screenshot_data)

    def _save_to_firebase(self, path: str, data: bytes) -> str:
        """Save to Firebase Storage and return signed URL."""
        try:
            blob = self.bucket.blob(path)
            blob.upload_from_string(data, content_type='image/png')

            # Generate signed URL valid for 7 days
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=SCREENSHOT_RETENTION_DAYS),
                method="GET"
            )

            logger.debug(f"Screenshot saved to Firebase: {path}")
            return url

        except Exception as e:
            logger.error(f"Failed to save screenshot to Firebase: {e}")
            raise

    def _save_to_local(self, path: str, data: bytes) -> str:
        """Save to local filesystem and return relative path."""
        try:
            full_path = self.local_root / path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, 'wb') as f:
                f.write(data)

            logger.debug(f"Screenshot saved locally: {full_path}")

            # Return URL path accessible via static mount
            # We mounted "screenshots" dir to "/screenshots" path
            # LOCAL_STORAGE_ROOT is "screenshots/simulations"
            # So the URL should be "/screenshots/simulations/" + path
            return f"/screenshots/simulations/{path}"

        except Exception as e:
            logger.error(f"Failed to save screenshot locally: {e}")
            raise

    def cleanup_old_screenshots(self, uid: Optional[str] = None) -> int:
        """
        Delete screenshots older than retention period.

        Args:
            uid: If provided, only clean up for this user. Otherwise clean all.

        Returns:
            Number of files deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=SCREENSHOT_RETENTION_DAYS)
        deleted_count = 0

        if self.mode == "firebase":
            deleted_count = self._cleanup_firebase(uid, cutoff_date)
        else:
            deleted_count = self._cleanup_local(uid, cutoff_date)

        logger.info(f"Cleaned up {deleted_count} old screenshots")
        return deleted_count

    def _cleanup_firebase(self, uid: Optional[str], cutoff_date: datetime) -> int:
        """Clean up Firebase Storage."""
        try:
            prefix = f"users/{uid}/simulations/" if uid else "users/"
            blobs = self.bucket.list_blobs(prefix=prefix)

            deleted_count = 0
            for blob in blobs:
                # Check blob creation time
                if blob.time_created and blob.time_created.replace(tzinfo=None) < cutoff_date:
                    blob.delete()
                    deleted_count += 1
                    logger.debug(f"Deleted old screenshot: {blob.name}")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up Firebase screenshots: {e}")
            return 0

    def _cleanup_local(self, uid: Optional[str], cutoff_date: datetime) -> int:
        """Clean up local filesystem."""
        try:
            if uid:
                search_path = self.local_root / "users" / uid / "simulations"
            else:
                search_path = self.local_root / "users"

            if not search_path.exists():
                return 0

            deleted_count = 0

            # Walk through all simulation directories
            for simulation_dir in search_path.rglob("*"):
                if not simulation_dir.is_dir():
                    continue

                # Check directory modification time
                mtime = datetime.fromtimestamp(simulation_dir.stat().st_mtime)
                if mtime < cutoff_date:
                    # Delete entire simulation directory
                    for file in simulation_dir.rglob("*"):
                        if file.is_file():
                            file.unlink()
                            deleted_count += 1

                    # Remove empty directories
                    for dir_path in sorted(simulation_dir.rglob("*"), reverse=True):
                        if dir_path.is_dir() and not any(dir_path.iterdir()):
                            dir_path.rmdir()

                    if not any(simulation_dir.iterdir()):
                        simulation_dir.rmdir()

                    logger.debug(f"Deleted old simulation directory: {simulation_dir}")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up local screenshots: {e}")
            return 0

    def get_simulation_screenshots(self, uid: str, timestamp: str) -> List[str]:
        """
        Get all screenshot URLs/paths for a simulation run.

        Args:
            uid: User ID
            timestamp: Simulation timestamp

        Returns:
            List of URLs (Firebase) or paths (local)
        """
        if self.mode == "firebase":
            return self._list_firebase_screenshots(uid, timestamp)
        else:
            return self._list_local_screenshots(uid, timestamp)

    def _list_firebase_screenshots(self, uid: str, timestamp: str) -> List[str]:
        """List screenshots from Firebase Storage."""
        try:
            prefix = f"users/{uid}/simulations/{timestamp}/"
            blobs = self.bucket.list_blobs(prefix=prefix)

            urls = []
            for blob in blobs:
                if blob.name.endswith('.png'):
                    url = blob.generate_signed_url(
                        version="v4",
                        expiration=timedelta(days=1),
                        method="GET"
                    )
                    urls.append(url)

            return sorted(urls)

        except Exception as e:
            logger.error(f"Error listing Firebase screenshots: {e}")
            return []

    def _list_local_screenshots(self, uid: str, timestamp: str) -> List[str]:
        """List screenshots from local filesystem."""
        try:
            simulation_dir = self.local_root / "users" / uid / "simulations" / timestamp

            if not simulation_dir.exists():
                return []

            paths = []
            for file in sorted(simulation_dir.glob("*.png")):
                # Return relative path
                rel_path = file.relative_to(self.local_root)
                # Ensure forward slashes for URL
                rel_path_str = str(rel_path).replace(os.path.sep, "/")
                paths.append(f"/screenshots/simulations/{rel_path_str}")

            return paths

        except Exception as e:
            logger.error(f"Error listing local screenshots: {e}")
            return []


# Singleton instance
_storage_instance: Optional[ScreenshotStorage] = None


def get_screenshot_storage() -> ScreenshotStorage:
    """Get singleton screenshot storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = ScreenshotStorage()
    return _storage_instance
