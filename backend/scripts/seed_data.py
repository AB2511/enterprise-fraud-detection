"""Seed database with realistic fraud detection data.

This script generates:
- 100 users (various roles)
- 1000 customers (various risk profiles)
- 500 merchants (various categories)
- 10,000 transactions (mix of fraud/legitimate)
- Sample alerts and predictions
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from faker import Faker

# Initialize faker
fake = Faker()


# =============================================================================
# Data Generation Functions
# =============================================================================


def generate_users(count: int = 100) -> list[dict]:
    """Generate user data.

    Args:
        count: Number of users to generate

    Returns:
        List of user dictionaries
    """
    roles = ["admin", "analyst", "data_scientist", "auditor", "viewer"]
    role_weights = [5, 40, 20, 20, 15]  # More analysts

    users = []
    for _i in range(count):
        role = random.choices(roles, weights=role_weights)[0]
        user = {
            "id": uuid4(),
            "email": fake.unique.email(),
            "hashed_password": "$2b$12$dummy_hash_for_seed_data_only",  # Placeholder
            "role": role,
            "status": "active" if random.random() > 0.1 else "inactive",
            "last_login_at": (
                fake.date_time_between(start_date="-30d", end_date="now")
                if random.random() > 0.3
                else None
            ),
            "created_at": fake.date_time_between(start_date="-2y", end_date="-1d"),
            "updated_at": datetime.utcnow(),
            "deleted_at": None,
        }
        users.append(user)

    return users


def generate_customers(count: int = 1000) -> list[dict]:
    """Generate customer data with various risk profiles.

    Args:
        count: Number of customers to generate

    Returns:
        List of customer dictionaries
    """
    countries = ["USA", "GBR", "DEU", "FRA", "JPN", "CAN", "AUS", "IND", "BRA", "MEX"]
    kyc_statuses = ["not_started", "pending", "verified", "rejected", "expired"]
    kyc_weights = [5, 10, 70, 10, 5]
    risk_categories = ["low", "medium", "high", "critical"]
    risk_weights = [50, 30, 15, 5]

    customers = []
    for _i in range(count):
        account_age_days = random.randint(1, 730)
        kyc_status = random.choices(kyc_statuses, weights=kyc_weights)[0]
        risk_category = random.choices(risk_categories, weights=risk_weights)[0]

        customer = {
            "id": uuid4(),
            "customer_name": fake.name(),
            "email": fake.unique.email(),
            "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=80),
            "country": random.choice(countries),
            "kyc_status": kyc_status,
            "customer_risk_category": risk_category,
            "historical_fraud_count": (
                random.randint(0, 5) if risk_category in ["high", "critical"] else 0
            ),
            "credit_score": random.randint(300, 850),
            "lifetime_transaction_volume": float(
                Decimal(random.uniform(0, 500000)).quantize(Decimal("0.01"))
            ),
            "account_age_days": account_age_days,
            "is_active": random.random() > 0.05,
            "created_at": fake.date_time_between(
                start_date=f"-{account_age_days}d", end_date=f"-{account_age_days}d"
            ),
            "updated_at": datetime.utcnow(),
            "deleted_at": None,
        }
        customers.append(customer)

    return customers


def generate_merchants(count: int = 500) -> list[dict]:
    """Generate merchant data with various MCCs.

    Args:
        count: Number of merchants to generate

    Returns:
        List of merchant dictionaries
    """
    categories = [
        ("5411", "grocery", "low"),
        ("5812", "restaurants", "low"),
        ("5999", "retail", "medium"),
        ("5732", "electronics", "high"),
        ("7995", "gambling", "high"),
        ("5942", "books", "low"),
        ("5941", "sporting_goods", "low"),
        ("4121", "travel", "high"),
        ("5912", "pharmaceuticals", "high"),
        ("7311", "advertising", "medium"),
    ]

    countries = ["USA", "GBR", "DEU", "FRA", "JPN", "CAN", "AUS"]

    merchants = []
    for _i in range(count):
        mcc, category, risk_level = random.choice(categories)

        # Risk rating based on category
        if risk_level == "low":
            risk_rating = random.randint(10, 40)
        elif risk_level == "medium":
            risk_rating = random.randint(40, 70)
        else:
            risk_rating = random.randint(70, 95)

        total_transactions = random.randint(100, 50000)
        fraud_rate = (
            random.uniform(0.1, 10.0) if risk_level == "high" else random.uniform(0.01, 2.0)
        )

        merchant = {
            "id": uuid4(),
            "merchant_name": fake.company(),
            "mcc": mcc,
            "merchant_category": category,
            "country": random.choice(countries),
            "risk_rating": risk_rating,
            "historical_fraud_rate": float(Decimal(fraud_rate).quantize(Decimal("0.01"))),
            "total_transactions": total_transactions,
            "total_volume": float(
                Decimal(random.uniform(10000, 5000000)).quantize(Decimal("0.01"))
            ),
            "is_active": random.random() > 0.05,
            "created_at": fake.date_time_between(start_date="-5y", end_date="-30d"),
            "updated_at": datetime.utcnow(),
            "deleted_at": None,
        }
        merchants.append(merchant)

    return merchants


def generate_transactions(
    customers: list[dict],
    merchants: list[dict],
    count: int = 10000,
) -> list[dict]:
    """Generate transaction data with realistic fraud patterns.

    Args:
        customers: List of customer dictionaries
        merchants: List of merchant dictionaries
        count: Number of transactions to generate

    Returns:
        List of transaction dictionaries
    """
    currencies = ["USD", "EUR", "GBP", "JPY", "CAD"]
    transaction_types = ["purchase", "refund", "withdrawal", "transfer"]
    statuses = ["pending", "approved", "declined", "failed"]
    channels = ["online", "pos", "atm", "mobile", "phone", "branch"]
    methods = ["credit_card", "debit_card", "bank_transfer", "wallet", "cash", "crypto"]

    transactions = []

    # Fraud patterns
    fraud_rate = 0.05  # 5% fraud
    high_risk_customers = [
        c for c in customers if c["customer_risk_category"] in ["high", "critical"]
    ]
    high_risk_merchants = [m for m in merchants if m["risk_rating"] >= 70]

    for _i in range(count):
        # Determine if transaction is fraud
        is_fraud = random.random() < fraud_rate

        if is_fraud and high_risk_customers:
            # Fraud more likely with high-risk customers/merchants
            customer = (
                random.choice(high_risk_customers)
                if random.random() > 0.3
                else random.choice(customers)
            )
            merchant = (
                random.choice(high_risk_merchants)
                if random.random() > 0.5 and high_risk_merchants
                else random.choice(merchants)
            )
        else:
            customer = random.choice(customers)
            merchant = random.choice(merchants)

        # Fraud patterns
        if is_fraud:
            # Higher amounts for fraud
            amount = float(Decimal(random.uniform(500, 10000)).quantize(Decimal("0.01")))
            status = "declined" if random.random() > 0.3 else "approved"
            channel = random.choice(["online", "mobile"])  # Fraud more common online
            method = random.choice(["credit_card", "wallet", "crypto"])
        else:
            amount = float(Decimal(random.uniform(5, 1000)).quantize(Decimal("0.01")))
            status = random.choices(statuses, weights=[10, 80, 5, 5])[0]
            channel = random.choice(channels)
            method = random.choice(methods)

        created_at = fake.date_time_between(start_date="-90d", end_date="now")

        transaction = {
            "id": uuid4(),
            "customer_id": customer["id"],
            "merchant_id": merchant["id"],
            "amount": amount,
            "currency": random.choice(currencies),
            "transaction_type": random.choice(transaction_types),
            "status": status,
            "payment_channel": channel,
            "payment_method": method,
            "terminal_id": f"TERM{random.randint(1000, 9999)}" if channel == "pos" else None,
            "device_id": fake.sha256()[:32] if channel in ["online", "mobile"] else None,
            "ip_address": fake.ipv4() if channel in ["online", "mobile"] else None,
            "latitude": float(fake.latitude()) if random.random() > 0.3 else None,
            "longitude": float(fake.longitude()) if random.random() > 0.3 else None,
            "velocity_1h": float(Decimal(random.uniform(0, 5)).quantize(Decimal("0.1"))),
            "velocity_24h": float(Decimal(random.uniform(0, 20)).quantize(Decimal("0.1"))),
            "velocity_7d": float(Decimal(random.uniform(0, 100)).quantize(Decimal("0.1"))),
            "is_fraud": is_fraud,
            "fraud_confirmed_at": (
                created_at + timedelta(hours=random.randint(1, 48))
                if is_fraud and random.random() > 0.5
                else None
            ),
            "created_at": created_at,
            "updated_at": datetime.utcnow(),
            "deleted_at": None,
        }
        transactions.append(transaction)

    return transactions


def generate_predictions(transactions: list[dict]) -> list[dict]:
    """Generate prediction data for transactions.

    Args:
        transactions: List of transaction dictionaries

    Returns:
        List of prediction dictionaries
    """
    predictions = []
    model_id = uuid4()
    model_version = "1.0.0"

    for txn in transactions:
        # Prediction accuracy: 90% correct
        actual_fraud = txn["is_fraud"]

        if random.random() < 0.9:  # 90% accurate
            predicted_fraud = actual_fraud
        else:
            predicted_fraud = not actual_fraud

        if predicted_fraud:
            fraud_probability = random.uniform(0.7, 0.99)
            anomaly_score = random.uniform(60, 95)
            risk_score = random.uniform(70, 100)
        else:
            fraud_probability = random.uniform(0.01, 0.3)
            anomaly_score = random.uniform(5, 40)
            risk_score = random.uniform(10, 50)

        prediction = {
            "id": uuid4(),
            "transaction_id": txn["id"],
            "model_id": model_id,
            "model_version": model_version,
            "prediction_class": "fraud" if predicted_fraud else "legitimate",
            "fraud_probability": float(Decimal(fraud_probability).quantize(Decimal("0.0001"))),
            "anomaly_score": float(Decimal(anomaly_score).quantize(Decimal("0.01"))),
            "risk_score": float(Decimal(risk_score).quantize(Decimal("0.01"))),
            "confidence": float(Decimal(random.uniform(0.8, 0.99)).quantize(Decimal("0.01"))),
            "decision": (
                "block"
                if fraud_probability > 0.8
                else "review"
                if fraud_probability > 0.5
                else "approve"
            ),
            "latency_ms": float(Decimal(random.uniform(10, 100)).quantize(Decimal("0.1"))),
            "explanation_data": {
                "top_features": [
                    {"feature": "amount", "contribution": random.uniform(-1, 1)},
                    {"feature": "velocity_24h", "contribution": random.uniform(-1, 1)},
                    {"feature": "customer_risk", "contribution": random.uniform(-1, 1)},
                ]
            },
            "created_at": txn["created_at"] + timedelta(milliseconds=50),
            "updated_at": datetime.utcnow(),
        }
        predictions.append(prediction)

    return predictions


def generate_alerts(predictions: list[dict], users: list[dict]) -> list[dict]:
    """Generate alert data for high-risk predictions.

    Args:
        predictions: List of prediction dictionaries
        users: List of user dictionaries

    Returns:
        List of alert dictionaries
    """
    analysts = [u for u in users if u["role"] == "analyst"]
    alert_types = [
        "high_amount",
        "velocity_anomaly",
        "location_mismatch",
        "device_anomaly",
        "merchant_risk",
        "customer_risk",
    ]
    statuses = ["open", "in_review", "resolved", "false_positive", "confirmed_fraud"]

    alerts = []

    # Create alerts for high-risk predictions (20% of predictions)
    high_risk_predictions = [p for p in predictions if p["fraud_probability"] > 0.7]
    alert_predictions = random.sample(high_risk_predictions, min(len(high_risk_predictions), 2000))

    for pred in alert_predictions:
        # Severity based on probability
        if pred["fraud_probability"] > 0.95:
            severity = "critical"
        elif pred["fraud_probability"] > 0.85:
            severity = "high"
        elif pred["fraud_probability"] > 0.75:
            severity = "medium"
        else:
            severity = "low"

        # Status distribution
        status = random.choices(statuses, weights=[20, 30, 30, 15, 5])[0]

        # Assignment
        assigned = status != "open"
        analyst = random.choice(analysts) if assigned and analysts else None

        # SLA hours based on severity
        sla_hours = {"critical": 1, "high": 4, "medium": 24, "low": 72}[severity]
        sla_deadline = pred["created_at"] + timedelta(hours=sla_hours)

        # Resolution
        resolved = status in ["resolved", "false_positive", "confirmed_fraud"]
        resolved_at = (
            pred["created_at"] + timedelta(hours=random.randint(1, 48)) if resolved else None
        )
        is_sla_breached = resolved_at > sla_deadline if resolved and resolved_at else False

        alert = {
            "id": uuid4(),
            "transaction_id": pred["transaction_id"],
            "prediction_id": pred["id"],
            "alert_type": random.choice(alert_types),
            "severity": severity,
            "status": status,
            "assigned_analyst_id": analyst["id"] if analyst else None,
            "assigned_at": (
                pred["created_at"] + timedelta(minutes=random.randint(5, 60)) if assigned else None
            ),
            "resolution": status if resolved else None,
            "resolved_at": resolved_at,
            "resolved_by_id": analyst["id"] if resolved and analyst else None,
            "sla_deadline": sla_deadline,
            "is_sla_breached": is_sla_breached,
            "created_at": pred["created_at"] + timedelta(minutes=1),
            "updated_at": datetime.utcnow(),
            "deleted_at": None,
        }
        alerts.append(alert)

    return alerts


# =============================================================================
# Main Execution
# =============================================================================


def main():
    """Generate and display seed data statistics."""
    print("=" * 80)
    print("FRAUD DETECTION SYSTEM - SEED DATA GENERATION")
    print("=" * 80)

    print("\n📊 Generating seed data...\n")

    # Generate data
    print("🔹 Generating users...")
    users = generate_users(100)
    print(f"   ✅ Generated {len(users)} users")

    print("🔹 Generating customers...")
    customers = generate_customers(1000)
    print(f"   ✅ Generated {len(customers)} customers")

    print("🔹 Generating merchants...")
    merchants = generate_merchants(500)
    print(f"   ✅ Generated {len(merchants)} merchants")

    print("🔹 Generating transactions...")
    transactions = generate_transactions(customers, merchants, 10000)
    print(f"   ✅ Generated {len(transactions)} transactions")

    print("🔹 Generating predictions...")
    predictions = generate_predictions(transactions)
    print(f"   ✅ Generated {len(predictions)} predictions")

    print("🔹 Generating alerts...")
    alerts = generate_alerts(predictions, users)
    print(f"   ✅ Generated {len(alerts)} alerts")

    # Statistics
    print("\n" + "=" * 80)
    print("📈 SEED DATA STATISTICS")
    print("=" * 80)

    print(f"\n👥 Users: {len(users)}")
    for role in ["admin", "analyst", "data_scientist", "auditor", "viewer"]:
        count = sum(1 for u in users if u["role"] == role)
        print(f"   • {role}: {count}")

    print(f"\n👤 Customers: {len(customers)}")
    for risk in ["low", "medium", "high", "critical"]:
        count = sum(1 for c in customers if c["customer_risk_category"] == risk)
        print(f"   • {risk} risk: {count}")

    print(f"\n🏪 Merchants: {len(merchants)}")
    categories = {m["merchant_category"] for m in merchants}
    for category in sorted(categories):
        count = sum(1 for m in merchants if m["merchant_category"] == category)
        print(f"   • {category}: {count}")

    print(f"\n💳 Transactions: {len(transactions)}")
    fraud_count = sum(1 for t in transactions if t["is_fraud"])
    print(
        f"   • Legitimate: {len(transactions) - fraud_count} ({((len(transactions) - fraud_count) / len(transactions) * 100):.1f}%)"
    )
    print(f"   • Fraud: {fraud_count} ({(fraud_count / len(transactions) * 100):.1f}%)")

    print(f"\n🎯 Predictions: {len(predictions)}")
    correct = sum(
        1
        for i, p in enumerate(predictions)
        if (p["prediction_class"] == "fraud") == transactions[i]["is_fraud"]
    )
    print(f"   • Accuracy: {(correct / len(predictions) * 100):.1f}%")

    print(f"\n🚨 Alerts: {len(alerts)}")
    for severity in ["low", "medium", "high", "critical"]:
        count = sum(1 for a in alerts if a["severity"] == severity)
        print(f"   • {severity}: {count}")

    print("\n" + "=" * 80)
    print("✅ Seed data generation complete!")
    print("=" * 80)

    print("\n💡 Next steps:")
    print("   1. Review the generated data above")
    print("   2. Use this script with SQLAlchemy to insert into database")
    print("   3. Or export to JSON/CSV for manual inspection")
    print("\n")


if __name__ == "__main__":
    main()
