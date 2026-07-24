"""IP Address Value Object."""

import ipaddress
from dataclasses import dataclass


@dataclass(frozen=True)
class IPAddress:
    """Value object representing an IP address.

    Attributes:
        address: The IP address string (IPv4 or IPv6)
    """

    address: str

    def __post_init__(self) -> None:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(self.address)
        except ValueError as e:
            raise ValueError(f"Invalid IP address: {self.address}") from e

    def is_private(self) -> bool:
        """Check if IP address is private.

        Returns:
            True if private IP address
        """
        ip = ipaddress.ip_address(self.address)
        return ip.is_private

    def is_loopback(self) -> bool:
        """Check if IP address is loopback.

        Returns:
            True if loopback address
        """
        ip = ipaddress.ip_address(self.address)
        return ip.is_loopback

    def is_ipv4(self) -> bool:
        """Check if address is IPv4.

        Returns:
            True if IPv4
        """
        try:
            ipaddress.IPv4Address(self.address)
            return True
        except ValueError:
            return False

    def is_ipv6(self) -> bool:
        """Check if address is IPv6.

        Returns:
            True if IPv6
        """
        try:
            ipaddress.IPv6Address(self.address)
            return True
        except ValueError:
            return False

    def anonymize(self) -> "IPAddress":
        """Anonymize IP address by masking last octet/segment.

        Returns:
            New IPAddress with anonymized address
        """
        ip = ipaddress.ip_address(self.address)

        if isinstance(ip, ipaddress.IPv4Address):
            # Mask last octet: 192.168.1.100 -> 192.168.1.0
            parts = self.address.split(".")
            parts[-1] = "0"
            return IPAddress(".".join(parts))
        else:
            # Mask last 64 bits of IPv6
            network = ipaddress.IPv6Network(f"{self.address}/64", strict=False)
            return IPAddress(str(network.network_address))

    def get_network(self, prefix_length: int) -> str:
        """Get network address with given prefix length.

        Args:
            prefix_length: Network prefix length

        Returns:
            Network address in CIDR notation
        """
        ip = ipaddress.ip_address(self.address)
        network: ipaddress.IPv4Network | ipaddress.IPv6Network
        if isinstance(ip, ipaddress.IPv4Address):
            network = ipaddress.IPv4Network(f"{self.address}/{prefix_length}", strict=False)
        else:
            network = ipaddress.IPv6Network(f"{self.address}/{prefix_length}", strict=False)

        return str(network)

    def __str__(self) -> str:
        """String representation."""
        return self.address
