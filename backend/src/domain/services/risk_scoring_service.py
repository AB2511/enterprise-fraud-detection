"""Risk Scoring Domain Service."""


class RiskScoringService:
    """Domain service for converting fraud probability to risk scores.

    This service encapsulates the business logic for risk score calculation,
    which doesn't naturally belong to any single entity.
    """

    def __init__(self, fraud_threshold: float = 0.5, high_risk_threshold: float = 0.8) -> None:
        """Initialize risk scoring service.

        Args:
            fraud_threshold: Probability threshold for fraud classification
            high_risk_threshold: Probability threshold for high-risk classification
        """
        if not (0 < fraud_threshold < 1):
            raise ValueError("Fraud threshold must be between 0 and 1")

        if not (fraud_threshold < high_risk_threshold < 1):
            raise ValueError("High risk threshold must be between fraud threshold and 1")

        self.fraud_threshold = fraud_threshold
        self.high_risk_threshold = high_risk_threshold

    def calculate_risk_score(self, fraud_probability: float) -> int:
        """Convert fraud probability to risk score [0, 100].

        Business rules:
        - Linear mapping from probability to score
        - Probability 0.0 -> Score 0
        - Probability 1.0 -> Score 100

        Args:
            fraud_probability: Fraud probability from model [0, 1]

        Returns:
            Risk score [0, 100]

        Raises:
            ValueError: If probability is out of range
        """
        if not (0.0 <= fraud_probability <= 1.0):
            raise ValueError("Fraud probability must be between 0 and 1")

        return int(fraud_probability * 100)

    def classify_risk_level(self, risk_score: int) -> str:
        """Classify risk score into risk levels.

        Business rules:
        - 0-30: Low risk
        - 31-60: Medium risk
        - 61-80: High risk
        - 81-100: Critical risk

        Args:
            risk_score: Risk score [0, 100]

        Returns:
            Risk level classification
        """
        if not (0 <= risk_score <= 100):
            raise ValueError("Risk score must be between 0 and 100")

        if risk_score <= 30:
            return "low"
        elif risk_score <= 60:
            return "medium"
        elif risk_score <= 80:
            return "high"
        else:
            return "critical"

    def should_block_transaction(self, fraud_probability: float) -> bool:
        """Determine if transaction should be automatically blocked.

        Business rule: Block if probability exceeds high-risk threshold.

        Args:
            fraud_probability: Fraud probability from model

        Returns:
            True if transaction should be blocked
        """
        return fraud_probability >= self.high_risk_threshold

    def should_manual_review(self, fraud_probability: float) -> bool:
        """Determine if transaction requires manual analyst review.

        Business rule: Review if probability is between fraud and high-risk thresholds.

        Args:
            fraud_probability: Fraud probability from model

        Returns:
            True if manual review is required
        """
        return self.fraud_threshold <= fraud_probability < self.high_risk_threshold
