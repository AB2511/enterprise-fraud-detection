"""Model Version Value Object."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelVersion:
    """Value object representing a semantic version for ML models.

    Follows semantic versioning: MAJOR.MINOR.PATCH

    Attributes:
        version: Version string (e.g., "1.2.3")
    """

    version: str

    def __post_init__(self) -> None:
        """Validate semantic version format."""
        if not self.version:
            raise ValueError("Version cannot be empty")

        # Validate semantic version format (MAJOR.MINOR.PATCH)
        pattern = r"^(\d+)\.(\d+)\.(\d+)$"
        if not re.match(pattern, self.version):
            raise ValueError(
                f"Invalid version format: {self.version}. "
                "Expected format: MAJOR.MINOR.PATCH (e.g., 1.2.3)"
            )

    @property
    def major(self) -> int:
        """Get major version number.

        Returns:
            Major version
        """
        return int(self.version.split(".")[0])

    @property
    def minor(self) -> int:
        """Get minor version number.

        Returns:
            Minor version
        """
        return int(self.version.split(".")[1])

    @property
    def patch(self) -> int:
        """Get patch version number.

        Returns:
            Patch version
        """
        return int(self.version.split(".")[2])

    def bump_major(self) -> "ModelVersion":
        """Increment major version (breaking changes).

        Returns:
            New ModelVersion with incremented major version
        """
        new_major = self.major + 1
        return ModelVersion(version=f"{new_major}.0.0")

    def bump_minor(self) -> "ModelVersion":
        """Increment minor version (new features).

        Returns:
            New ModelVersion with incremented minor version
        """
        new_minor = self.minor + 1
        return ModelVersion(version=f"{self.major}.{new_minor}.0")

    def bump_patch(self) -> "ModelVersion":
        """Increment patch version (bug fixes).

        Returns:
            New ModelVersion with incremented patch version
        """
        new_patch = self.patch + 1
        return ModelVersion(version=f"{self.major}.{self.minor}.{new_patch}")

    def is_compatible_with(self, other: "ModelVersion") -> bool:
        """Check if version is backward compatible.

        Versions are compatible if major version matches.

        Args:
            other: Other ModelVersion to compare

        Returns:
            True if compatible
        """
        return self.major == other.major

    def is_newer_than(self, other: "ModelVersion") -> bool:
        """Check if this version is newer than another.

        Args:
            other: Other ModelVersion to compare

        Returns:
            True if this version is newer
        """
        if self.major != other.major:
            return self.major > other.major
        if self.minor != other.minor:
            return self.minor > other.minor
        return self.patch > other.patch

    def is_breaking_change(self, other: "ModelVersion") -> bool:
        """Check if upgrade would be a breaking change.

        Args:
            other: Target version

        Returns:
            True if major version differs
        """
        return self.major != other.major

    @classmethod
    def parse(cls, version_str: str) -> "ModelVersion":
        """Parse version string into ModelVersion.

        Args:
            version_str: Version string to parse

        Returns:
            New ModelVersion instance
        """
        return cls(version=version_str)

    @classmethod
    def initial(cls) -> "ModelVersion":
        """Create initial version (1.0.0).

        Returns:
            New ModelVersion at 1.0.0
        """
        return cls(version="1.0.0")

    def __str__(self) -> str:
        """String representation."""
        return self.version

    def __lt__(self, other: object) -> bool:
        """Less than comparison."""
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return not self.is_newer_than(other) and self.version != other.version

    def __le__(self, other: object) -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return not self.is_newer_than(other)

    def __gt__(self, other: object) -> bool:
        """Greater than comparison."""
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return self.is_newer_than(other)

    def __ge__(self, other: object) -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return self.is_newer_than(other) or self.version == other.version
