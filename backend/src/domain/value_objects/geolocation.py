"""Geolocation Value Object."""

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt


@dataclass(frozen=True)
class Geolocation:
    """Geolocation value object representing geographic coordinates.

    Attributes:
        latitude: Latitude in decimal degrees (-90 to 90)
        longitude: Longitude in decimal degrees (-180 to 180)
    """

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        """Validate geolocation coordinates."""
        if not (-90 <= self.latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90")

        if not (-180 <= self.longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180")

    def distance_to(self, other: "Geolocation") -> float:
        """Calculate haversine distance to another location in kilometers.

        Args:
            other: Another geolocation

        Returns:
            Distance in kilometers
        """
        earth_radius_km = 6371.0

        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(other.latitude), radians(other.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))

        return earth_radius_km * c

    @property
    def is_valid(self) -> bool:
        """Check if coordinates are valid (not null island)."""
        return not (self.latitude == 0.0 and self.longitude == 0.0)
