"""Payment Channel Enumeration."""

from enum import StrEnum


class PaymentChannel(StrEnum):
    """Channel through which payment was made.

    Attributes:
        ONLINE: Online/e-commerce transaction
        POS: Point of sale (physical terminal)
        ATM: Automated teller machine
        MOBILE: Mobile app or mobile wallet
        PHONE: Phone banking or IVR
        BRANCH: In-branch transaction
    """

    ONLINE = "online"
    POS = "pos"
    ATM = "atm"
    MOBILE = "mobile"
    PHONE = "phone"
    BRANCH = "branch"

    def is_card_present(self) -> bool:
        """Check if channel typically requires physical card.

        Returns:
            True if card-present channel
        """
        return self in {PaymentChannel.POS, PaymentChannel.ATM, PaymentChannel.BRANCH}

    def get_risk_multiplier(self) -> float:
        """Get risk multiplier for channel.

        Returns:
            Risk multiplier (1.0 = baseline)
        """
        risk_map = {
            PaymentChannel.ONLINE: 1.5,
            PaymentChannel.MOBILE: 1.3,
            PaymentChannel.PHONE: 1.4,
            PaymentChannel.POS: 1.0,
            PaymentChannel.ATM: 1.1,
            PaymentChannel.BRANCH: 0.8,
        }
        return risk_map[self]
