"""Device ID Value Object."""

import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceID:
    """Value object representing a device fingerprint/ID.

    Device IDs are used to track devices across transactions for fraud detection.

    Attributes:
        device_id: The device identifier string
    """

    device_id: str

    def __post_init__(self) -> None:
        """Validate device ID format."""
        if not self.device_id:
            raise ValueError("Device ID cannot be empty")

        if len(self.device_id) < 8:
            raise ValueError("Device ID must be at least 8 characters")

        if len(self.device_id) > 256:
            raise ValueError("Device ID cannot exceed 256 characters")

        # Allow alphanumeric, hyphens, and underscores
        if not re.match(r"^[a-zA-Z0-9\-_]+$", self.device_id):
            raise ValueError(
                "Device ID can only contain alphanumeric characters, hyphens, and underscores"
            )

    def hash(self) -> str:
        """Generate SHA256 hash of device ID.

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(self.device_id.encode()).hexdigest()

    def anonymize(self) -> str:
        """Anonymize device ID by hashing.

        Returns:
            Hashed device ID (first 16 characters)
        """
        full_hash = self.hash()
        return full_hash[:16]

    def matches_pattern(self, pattern: str) -> bool:
        """Check if device ID matches a pattern.

        Args:
            pattern: Pattern prefix to match

        Returns:
            True if device ID starts with pattern
        """
        return self.device_id.startswith(pattern)

    def is_mobile(self) -> bool:
        """Check if device ID appears to be from mobile device.

        Returns:
            True if mobile device patterns detected
        """
        mobile_patterns = ["mobile", "android", "ios", "iphone", "ipad"]
        device_lower = self.device_id.lower()
        return any(pattern in device_lower for pattern in mobile_patterns)

    def is_web(self) -> bool:
        """Check if device ID appears to be from web browser.

        Returns:
            True if web browser patterns detected
        """
        web_patterns = ["chrome", "firefox", "safari", "edge", "browser"]
        device_lower = self.device_id.lower()
        return any(pattern in device_lower for pattern in web_patterns)

    @classmethod
    def from_fingerprint(cls, user_agent: str, screen_res: str, timezone: str) -> "DeviceID":
        """Create device ID from browser fingerprint components.

        Args:
            user_agent: User agent string
            screen_res: Screen resolution (e.g., "1920x1080")
            timezone: Timezone offset

        Returns:
            New DeviceID instance
        """
        fingerprint_str = f"{user_agent}|{screen_res}|{timezone}"
        device_hash = hashlib.sha256(fingerprint_str.encode()).hexdigest()
        return cls(device_id=device_hash[:32])

    def __str__(self) -> str:
        """String representation."""
        return self.device_id
