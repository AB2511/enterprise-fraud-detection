# ML Design Specification
# Enterprise Fraud Detection Platform

**Version:** 1.0  
**Date:** July 7, 2026  
**Status:** Design Phase  
**Authors:** ML Engineering Team  
**Reviewers:** Product, Engineering, Risk Management, Compliance

---

## Document Purpose

This specification defines the complete machine learning system design for fraud detection **before any code implementation**. It serves as the single source of truth for all ML-related decisions, architectures, and strategies.

**This is a design document only. No code implementation is included.**

---

## Executive Summary

### Business Problem
Financial fraud causes billions in annual losses. The platform must detect fraudulent transactions in real-time with high accuracy while minimizing false positives that harm customer experience and operational costs.

### Solution Approach
Hybrid ensemble combining:
- **XGBoost** for supervised classification (labeled fraud patterns)
- **Isolation Forest** for unsupervised anomaly detection (novel fraud patterns)

### Success Metrics
- **Precision ≥ 85%** - Minimize false positives (legitimate transactions flagged as fraud)
- **Recall ≥ 75%** - Catch majority of actual fraud
- **Latency < 100ms** - Real-time inference (p95)
- **Cost Savings ≥ $10M annually** - Net benefit after operational costs

---

## Table of Contents

1. [Data Specification](#1-data-specification)
2. [Feature Engineering](#2-feature-engineering)
3. [Target Definition](#3-target-definition)
4. [Pipeline Architecture](#4-pipeline-architecture)
5. [Model Selection](#5-model-selection)
6. [Evaluation Strategy](#6-evaluation-strategy)
7. [Explainability](#7-explainability)
8. [Monitoring Strategy](#8-monitoring-strategy)
9. [Risk Management](#9-risk-management)
10. [Deployment Strategy](#10-deployment-strategy)
11. [Deliverables](#11-deliverables)

---

## 1. Data Specification

### 1.1 Dataset Source

#### Primary Data Source
- **Source Type:** Internal transaction database
- **Collection Method:** Real-time transaction stream + historical batch data
- **Volume:** 
  - Historical: 50M transactions (2 years)
  - Daily: ~70K new transactions
  - Fraud rate: ~0.5% (25K fraud cases in historical data)
- **Update Frequency:** Real-time streaming + nightly batch updates
- **Data Ownership:** Company-owned, no external datasets

#### License & Legal
- **Data License:** Proprietary - Company owns all transaction data
- **Legal Compliance:**
  - GDPR compliant (EU customers)
  - PCI-DSS Level 1 compliant (payment card data)
  - CCPA compliant (California customers)
  - Data retention: 7 years (regulatory requirement)
- **PII Handling:** 
  - Customer names, emails, addresses are PII
  - Must be anonymized in ML pipeline
  - Use customer_id hash instead of identifiable information
- **Consent:** Covered under Terms of Service (fraud prevention is legitimate interest under GDPR Article 6(1)(f))

### 1.2 Schema Definition

#### Transaction Table
```
transaction_id: UUID (Primary Key)
customer_id: UUID (Foreign Key → customers)
merchant_id: UUID (Foreign Key → merchants)
timestamp: TIMESTAMP (UTC)
amount: DECIMAL(15,2)
currency: VARCHAR(3)
transaction_type: ENUM (purchase, refund, withdrawal, transfer)
payment_method: VARCHAR(50) (credit_card, debit_card, bank_transfer, digital_wallet)
card_type: VARCHAR(50) (visa, mastercard, amex, discover, NULL if not card)
device_id: VARCHAR(255) (browser fingerprint or mobile device ID)
ip_address: VARCHAR(45) (IPv4 or IPv6)
latitude: DECIMAL(10,8) (transaction location)
longitude: DECIMAL(11,8) (transaction location)
merchant_category_code: VARCHAR(4) (MCC code)
is_online: BOOLEAN (online vs in-person transaction)
is_international: BOOLEAN (cross-border transaction)
fraud_label: BOOLEAN (ground truth, NULL for unlabeled)
fraud_reported_at: TIMESTAMP (when fraud was reported, NULL if not fraud)
investigator_id: UUID (who labeled it, NULL if not investigated)
status: ENUM (pending, approved, declined, reversed)
```

#### Customer Table (features only, full schema in domain model)
```
customer_id: UUID
account_age_days: INTEGER
kyc_status: ENUM (pending, verified, rejected)
customer_risk_category: ENUM (low, medium, high, critical)
historical_fraud_count: INTEGER
credit_score: INTEGER (300-850)
lifetime_transaction_volume: DECIMAL(15,2)
country: VARCHAR(3) (ISO 3166-1 alpha-3)
```

#### Merchant Table
```
merchant_id: UUID
merchant_name: VARCHAR(255)
merchant_category: VARCHAR(100)
merchant_risk_score: DECIMAL(5,2) (0-100)
fraud_rate_30d: DECIMAL(5,4) (rolling 30-day fraud rate)
transaction_count_30d: INTEGER
merchant_country: VARCHAR(3)
is_verified: BOOLEAN
```

### 1.3 Class Imbalance

#### Distribution
- **Fraud (Positive Class):** ~0.5% (1 in 200 transactions)
- **Legitimate (Negative Class):** ~99.5%
- **Imbalance Ratio:** 1:200

#### Business Impact
- **False Positive Cost:** ~$25 per transaction
  - Customer service investigation
  - Customer frustration/churn risk
  - Operational overhead
- **False Negative Cost:** ~$500 per transaction
  - Direct financial loss
  - Chargeback fees
  - Regulatory fines
  - Reputation damage

**Cost Ratio:** FN is 20x more expensive than FP

#### Mitigation Strategies
1. **SMOTE (Synthetic Minority Over-sampling):** Generate synthetic fraud examples (training only)
2. **Class Weights:** Penalize FN 20x more than FP in loss function
3. **Stratified Sampling:** Ensure fraud cases in all splits
4. **Ensemble:** Combine models with different class handling strategies
5. **Threshold Tuning:** Optimize decision threshold for business cost (not 0.5)

### 1.4 Data Quality Assumptions

#### Completeness
- **Required fields:** 100% complete (transaction_id, customer_id, merchant_id, amount, timestamp)
- **Optional fields:** May have nulls (latitude/longitude ~30% null, card_type ~40% null)
- **Assumption:** Missing geolocation indicates online transaction (validated with is_online flag)

#### Accuracy
- **Amount:** Accurate to 2 decimal places (currency precision)
- **Timestamp:** Server-side timestamp (UTC), not client-side (prevents manipulation)
- **Geolocation:** IP-based or GPS (±50m accuracy), can be VPN/proxy
- **Assumption:** Timestamps are tamper-proof (application layer validation)

#### Timeliness
- **Label Delay:** Fraud reports arrive 0-90 days after transaction
  - 40% reported within 24 hours (card stolen/lost)
  - 30% reported within 7 days (statement review)
  - 20% reported within 30 days (detailed review)
  - 10% reported after 30 days (dispute process)
- **Impact:** Recent transactions are unlabeled (online learning required)

#### Consistency
- **Currency Conversion:** All amounts stored in original currency, converted to USD for modeling
- **Timezone:** All timestamps in UTC
- **Country Codes:** ISO 3166-1 alpha-3 standard
- **Assumption:** Data warehouse ETL maintains consistency

### 1.5 Preprocessing Requirements

#### Data Cleaning
1. **Duplicate Removal:** 
   - Detect: Same transaction_id or (customer_id, merchant_id, amount, timestamp within 1 second)
   - Action: Keep first occurrence, log duplicates
   - Expected rate: <0.01%

2. **Outlier Handling:**
   - Amount outliers: Transactions >$50,000 flagged for manual review (keep in data)
   - Geolocation outliers: Impossible travel (>500 mph between transactions) → nullify location
   - Expected rate: ~0.1%

3. **Missing Value Strategy:**
   - Categorical: Create "UNKNOWN" category
   - Numerical: Impute with median (if <5% missing) or create missing indicator feature
   - Geolocation: NULL → is_location_available=False feature

4. **Data Validation:**
   - Amount > 0 (refunds handled separately)
   - Timestamp < current_time (no future transactions)
   - Currency in valid ISO 4217 codes
   - Invalid records: Log and exclude (<0.01% expected)

---

## 2. Feature Engineering

### 2.1 Feature Dictionary

Total Features: 47 (35 raw + 12 engineered)

#### 2.1.1 Transaction Features (10 features)

**F1: transaction_amount**
- **Meaning:** Transaction value in USD (normalized from original currency)
- **Type:** Numerical (continuous)
- **Range:** [0.01, 50000.00] (99.9th percentile)
- **Transformation:** Log transform (log1p) to handle skewness
- **Importance:** HIGH - Fraud patterns differ by amount bracket
- **Business Justification:** Large amounts attract fraud; micro-transactions often test stolen cards

**F2: transaction_hour**
- **Meaning:** Hour of day when transaction occurred (0-23)
- **Type:** Numerical (discrete) 
- **Range:** [0, 23]
- **Transformation:** Cyclical encoding (sin/cos) to capture 23→0 continuity
- **Importance:** MEDIUM - Fraud spikes at unusual hours (3-5 AM)
- **Business Justification:** Legitimate users have regular patterns; fraudsters operate 24/7

**F3: transaction_day_of_week**
- **Meaning:** Day of week (0=Monday, 6=Sunday)
- **Type:** Categorical (ordinal)
- **Range:** [0, 6]
- **Transformation:** One-hot encoding
- **Importance:** LOW-MEDIUM - Weekend patterns differ
- **Business Justification:** Fraud attempts spike on weekends (less monitoring)

**F4: transaction_type**
- **Meaning:** Type of transaction (purchase, withdrawal, transfer, refund)
- **Type:** Categorical (nominal)
- **Range:** {purchase, withdrawal, transfer, refund}
- **Transformation:** One-hot encoding (4 binary features)
- **Importance:** HIGH - Withdrawals have 3x higher fraud rate
- **Business Justification:** Cash-out methods preferred by fraudsters

**F5: payment_method**
- **Meaning:** Payment instrument used
- **Type:** Categorical (nominal)
- **Range:** {credit_card, debit_card, bank_transfer, digital_wallet, other}
- **Transformation:** One-hot encoding
- **Importance:** MEDIUM - Credit cards more vulnerable
- **Business Justification:** Different methods have different fraud vectors

**F6: is_online**
- **Meaning:** Online (card-not-present) vs in-person transaction
- **Type:** Binary
- **Range:** {0, 1}
- **Transformation:** None
- **Importance:** HIGH - Online fraud rate 5x higher than in-person
- **Business Justification:** CNP transactions lack physical card verification

**F7: is_international**
- **Meaning:** Cross-border transaction (customer country ≠ merchant country)
- **Type:** Binary
- **Range:** {0, 1}
- **Transformation:** None
- **Importance:** HIGH - International transactions 4x fraud rate
- **Business Justification:** Harder to track, exploit currency arbitrage

**F8: merchant_category_code**
- **Meaning:** MCC (4-digit code for merchant type)
- **Type:** Categorical (nominal, high cardinality ~300 categories)
- **Range:** 4-digit codes (e.g., 5411=grocery, 5812=restaurants)
- **Transformation:** Target encoding (mean fraud rate per category)
- **Importance:** MEDIUM-HIGH - Some categories (electronics, travel) higher risk
- **Business Justification:** Fraud concentrates in resellable goods categories

**F9: distance_from_home**
- **Meaning:** Haversine distance (km) between transaction location and customer home
- **Type:** Numerical (continuous)
- **Range:** [0, 20000] km
- **Transformation:** Log transform
- **Importance:** HIGH - Sudden location changes indicate card theft
- **Business Justification:** Legitimate users have predictable geographic patterns

**F10: impossible_travel_flag**
- **Meaning:** Transaction location impossible given time since last transaction
- **Type:** Binary (engineered)
- **Range:** {0, 1}
- **Calculation:** distance / time_since_last_txn > 500 mph (airplane speed)
- **Importance:** CRITICAL - Strong fraud signal
- **Business Justification:** Physical card cannot teleport

#### 2.1.2 Customer Features (12 features)

**F11: customer_age_days**
- **Meaning:** Days since account creation
- **Type:** Numerical (discrete)
- **Range:** [0, 3650] (10 years max in dataset)
- **Transformation:** Log transform
- **Importance:** HIGH - New accounts 10x fraud rate
- **Business Justification:** Fraudsters create new accounts; established customers trusted

**F12: customer_kyc_status**
- **Meaning:** KYC verification status
- **Type:** Categorical (ordinal)
- **Range:** {pending, verified, rejected}
- **Transformation:** Ordinal encoding (pending=0, verified=1, rejected=2)
- **Importance:** CRITICAL - Unverified accounts blocked from high-value transactions
- **Business Justification:** KYC is regulatory fraud prevention requirement

**F13: customer_risk_category**
- **Meaning:** Pre-computed customer risk score category
- **Type:** Categorical (ordinal)
- **Range:** {low, medium, high, critical}
- **Transformation:** Ordinal encoding (0-3)
- **Importance:** HIGH - Domain expert risk assessment
- **Business Justification:** Incorporates historical behavior, fraud history, credit score

**F14: customer_historical_fraud_count**
- **Meaning:** Number of confirmed fraud cases for this customer (lifetime)
- **Type:** Numerical (discrete, count)
- **Range:** [0, 50] (capped at 50, accounts closed after repeated fraud)
- **Transformation:** None (already interpretable)
- **Importance:** CRITICAL - Past fraud predicts future fraud
- **Business Justification:** Repeat victims (card stolen multiple times) or fraudsters

**F15: customer_credit_score**
- **Meaning:** FICO-style credit score
- **Type:** Numerical (discrete)
- **Range:** [300, 850]
- **Transformation:** Standardization (mean=0, std=1)
- **Importance:** MEDIUM - Low scores correlate with higher fraud (desperation)
- **Business Justification:** Financial stress increases fraud temptation

**F16: customer_lifetime_transaction_volume**
- **Meaning:** Total USD transacted by customer (all time)
- **Type:** Numerical (continuous)
- **Range:** [0, 10M]
- **Transformation:** Log transform
- **Importance:** MEDIUM - Established customers less risky
- **Business Justification:** High-volume legitimate users build trust

**F17: customer_avg_transaction_amount**
- **Meaning:** Historical average transaction size for this customer
- **Type:** Numerical (continuous, engineered)
- **Range:** [0, 50000]
- **Transformation:** Log transform
- **Calculation:** lifetime_volume / transaction_count
- **Importance:** HIGH - Sudden deviations indicate compromise
- **Business Justification:** Users have consistent spending patterns

**F18: customer_transaction_count_7d**
- **Meaning:** Number of transactions in past 7 days
- **Type:** Numerical (discrete, count, engineered)
- **Range:** [0, 500]
- **Transformation:** None
- **Importance:** HIGH - Velocity feature (rapid-fire transactions suspicious)
- **Business Justification:** Fraudsters maximize theft before detection

**F19: customer_transaction_count_30d**
- **Meaning:** Number of transactions in past 30 days
- **Type:** Numerical (discrete, count, engineered)
- **Range:** [0, 2000]
- **Transformation:** None
- **Importance:** MEDIUM - Long-term activity pattern
- **Business Justification:** Inactive accounts suddenly active = compromise

**F20: customer_declined_transactions_7d**
- **Meaning:** Number of declined transactions in past 7 days
- **Type:** Numerical (discrete, count, engineered)
- **Range:** [0, 100]
- **Transformation:** None
- **Importance:** CRITICAL - Card testing behavior
- **Business Justification:** Fraudsters probe limits with small failed transactions

**F21: customer_unique_merchants_30d**
- **Meaning:** Number of distinct merchants used in past 30 days
- **Type:** Numerical (discrete, count, engineered)
- **Range:** [0, 200]
- **Transformation:** None
- **Importance:** MEDIUM - Diversity of spending
- **Business Justification:** Sudden new merchants = pattern break

**F22: customer_max_transaction_amount_30d**
- **Meaning:** Largest transaction in past 30 days
- **Type:** Numerical (continuous, engineered)
- **Range:** [0, 50000]
- **Transformation:** Log transform
- **Importance:** MEDIUM - Historical ceiling for spending
- **Business Justification:** Exceeding past maximum is anomalous

#### 2.1.3 Merchant Features (8 features)

**F23: merchant_fraud_rate_30d**
- **Meaning:** Rolling 30-day fraud rate for this merchant
- **Type:** Numerical (continuous)
- **Range:** [0.0, 1.0] (percentage as decimal)
- **Transformation:** None (already 0-1 range)
- **Importance:** CRITICAL - Compromised merchants or fraud rings
- **Business Justification:** Some merchants are fraud hotspots (skimmers, data breaches)

**F24: merchant_risk_score**
- **Meaning:** Pre-computed merchant risk (compliance, chargebacks, industry)
- **Type:** Numerical (continuous)
- **Range:** [0, 100]
- **Transformation:** Standardization
- **Importance:** HIGH - Domain expert merchant assessment
- **Business Justification:** High-risk merchants (offshore, gambling, crypto) targeted

**F25: merchant_transaction_count_30d**
- **Meaning:** Merchant's total transaction volume (past 30 days)
- **Type:** Numerical (discrete, count)
- **Range:** [0, 1M]
- **Transformation:** Log transform
- **Importance:** LOW-MEDIUM - Merchant size/legitimacy
- **Business Justification:** Very small merchants riskier (pop-up scams)

**F26: merchant_avg_transaction_amount**
- **Meaning:** Average transaction size for this merchant (all time)
- **Type:** Numerical (continuous)
- **Range:** [0, 50000]
- **Transformation:** Log transform
- **Importance:** MEDIUM - Merchant pricing pattern
- **Business Justification:** Transaction far from merchant average = anomaly

**F27: merchant_is_verified**
- **Meaning:** Merchant has completed verification process
- **Type:** Binary
- **Range:** {0, 1}
- **Transformation:** None
- **Importance:** MEDIUM - Trust signal
- **Business Justification:** Unverified merchants higher risk (shell companies)

**F28: merchant_country_risk**
- **Meaning:** Country risk score for merchant location
- **Type:** Numerical (continuous)
- **Range:** [0, 100]
- **Source:** External risk index (Transparency International CPI)
- **Transformation:** Standardization
- **Importance:** MEDIUM - Geopolitical fraud risk
- **Business Justification:** High-corruption countries have higher fraud rates

**F29: merchant_category_fraud_rate**
- **Meaning:** Historical fraud rate for merchant's category (e.g., electronics)
- **Type:** Numerical (continuous, engineered)
- **Range:** [0.0, 1.0]
- **Transformation:** None
- **Importance:** HIGH - Industry risk profile
- **Business Justification:** Electronics/jewelry/travel have higher fraud rates

**F30: merchant_chargeback_rate_30d**
- **Meaning:** Rolling 30-day chargeback rate (disputes/total transactions)
- **Type:** Numerical (continuous)
- **Range:** [0.0, 1.0]
- **Transformation:** None
- **Importance:** HIGH - Indirect fraud signal
- **Business Justification:** High chargebacks indicate fraud or poor service

#### 2.1.4 Temporal Features (7 features)

**F31: time_since_last_transaction**
- **Meaning:** Seconds since customer's previous transaction
- **Type:** Numerical (continuous, engineered)
- **Range:** [0, 31536000] (1 year max)
- **Transformation:** Log transform
- **Importance:** HIGH - Velocity feature
- **Business Justification:** Rapid-fire transactions = card testing or fraud spree

**F32: time_since_account_creation**
- **Meaning:** Days since customer account created (duplicate of F11, included for clarity)
- **Type:** Numerical (continuous)
- **Range:** [0, 3650]
- **Transformation:** Log transform
- **Importance:** HIGH - Account age risk
- **Business Justification:** New accounts higher risk

**F33: hour_deviation_from_customer_norm**
- **Meaning:** |transaction_hour - customer_avg_hour| (absolute deviation)
- **Type:** Numerical (continuous, engineered)
- **Range:** [0, 12] (max deviation in 24-hour cycle)
- **Transformation:** None
- **Importance:** MEDIUM-HIGH - Behavioral anomaly
- **Business Justification:** Users transact at consistent times (work hours, evenings)

**F34: is_weekend**
- **Meaning:** Transaction occurred on Saturday or Sunday
- **Type:** Binary (engineered)
- **Range:** {0, 1}
- **Transformation:** None
- **Importance:** LOW-MEDIUM - Temporal pattern
- **Business Justification:** Fraud attempts increase when monitoring reduced

**F35: is_night_time**
- **Meaning:** Transaction occurred between 11 PM and 5 AM local time
- **Type:** Binary (engineered)
- **Range:** {0, 1}
- **Transformation:** None
- **Importance:** MEDIUM - Unusual activity hours
- **Business Justification:** Legitimate transactions rare at night (excluding bars/restaurants)

**F36: days_since_last_fraud_report**
- **Meaning:** Days since customer last reported fraud (NULL if never reported)
- **Type:** Numerical (continuous, engineered)
- **Range:** [0, 3650] or NULL
- **Transformation:** Log transform, NULL indicator feature
- **Importance:** HIGH - Repeat victim pattern
- **Business Justification:** Fraud victims often targeted again (leaked data)

**F37: transaction_velocity_score**
- **Meaning:** Composite velocity score (transactions per hour, past 24h)
- **Type:** Numerical (continuous, engineered)
- **Range:** [0, 100]
- **Calculation:** (txn_count_24h / 24) * 100, capped at 100
- **Transformation:** None
- **Importance:** HIGH - Rapid-fire detection
- **Business Justification:** Fraudsters maximize theft speed before card blocked

#### 2.1.5 Interaction Features (10 features)

**F38: amount_to_customer_avg_ratio**
- **Meaning:** transaction_amount / customer_avg_transaction_amount
- **Type:** Numerical (continuous, engineered)
- **Range:** [0, 1000] (capped at 1000x)
- **Transformation:** Log transform
- **Importance:** CRITICAL - Deviation from norm
- **Business Justification:** Sudden large purchases = stolen card

**F39: amount_to_merchant_avg_ratio**
- **Meaning:** transaction_amount / merchant_avg_transaction_amount
- **Type:** Numerical (continuous, engineered)
- **Range:** [0, 100] (capped at 100x)
- **Transformation:** Log transform
- **Importance:** HIGH - Unusual for merchant
- **Business Justification:** Fraudsters may overpay or underpay

**F40: customer_merchant_interaction_count**
- **Meaning:** Number of past transactions between this customer and merchant
- **Type:** Numerical (discrete, count, engineered)
- **Range:** [0, 1000]
- **Transformation:** None
- **Importance:** MEDIUM - Relationship strength
- **Business Justification:** First-time interactions riskier

**F41: customer_new_merchant_flag**
- **Meaning:** First transaction with this merchant for customer
- **Type:** Binary (engineered)
- **Range:** {0, 1}
- **Calculation:** customer_merchant_interaction_count == 0
- **Transformation:** None
- **Importance:** MEDIUM-HIGH - New relationship
- **Business Justification:** Fraudsters use card at unfamiliar merchants

**F42: amount_times_merchant_risk**
- **Meaning:** transaction_amount * merchant_risk_score
- **Type:** Numerical (continuous, engineered)
- **Range:** [0, 5M] (50K * 100)
- **Transformation:** Log transform
- **Importance:** HIGH - Combined risk
- **Business Justification:** Large transactions at risky merchants = double red flag

**F43: is_high_risk_combination**
- **Meaning:** High-risk customer + high-risk merchant + high-risk category
- **Type:** Binary (engineered)
- **Range:** {0, 1}
- **Calculation:** (customer_risk_category >= 'high') AND (merchant_risk_score > 70) AND (merchant_category_fraud_rate > 0.02)
- **Transformation:** None
- **Importance:** HIGH - Triple threat
- **Business Justification:** All risk factors aligned = investigate

**F44: international_mismatch_flag**
- **Meaning:** Customer country ≠ merchant country ≠ transaction location country
- **Type:** Binary (engineered)
- **Range:** {0, 1}
- **Transformation:** None
- **Importance:** MEDIUM-HIGH - Geographic anomaly
- **Business Justification:** Complex cross-border patterns suspicious

**F45: device_mismatch_flag**
- **Meaning:** Transaction device_id not seen in past 30 days for customer
- **Type:** Binary (engineered)
- **Range:** {0, 1}
- **Transformation:** None
- **Importance:** HIGH - New device
- **Business Justification:** Stolen cards used on fraudster's device

**F46: ip_mismatch_flag**
- **Meaning:** Transaction IP address not seen in past 30 days for customer
- **Type:** Binary (engineered)
- **Range:** {0, 1}
- **Transformation:** None
- **Importance:** MEDIUM-HIGH - New network
- **Business Justification:** Sudden IP changes = compromised account

**F47: velocity_times_amount**
- **Meaning:** transaction_velocity_score * transaction_amount
- **Type:** Numerical (continuous, engineered)
- **Range:** [0, 5M] (100 * 50K)
- **Transformation:** Log transform
- **Importance:** HIGH - Speed and size
- **Business Justification:** Fast high-value transactions = maximize theft

### 2.2 Feature Importance Ranking (Expected)

**Tier 1 - Critical (>10% importance):**
1. customer_historical_fraud_count (15%)
2. impossible_travel_flag (12%)
3. amount_to_customer_avg_ratio (11%)
4. merchant_fraud_rate_30d (10%)

**Tier 2 - High (5-10% importance):**
5. customer_kyc_status (9%)
6. transaction_amount (8%)
7. customer_age_days (7%)
8. customer_declined_transactions_7d (7%)
9. is_international (6%)
10. time_since_last_transaction (6%)

**Tier 3 - Medium (2-5% importance):**
11-25. Various engineered features and aggregations (~2-4% each)

**Tier 4 - Low (<2% importance):**
26-47. Supporting features and rare event indicators

*Note: Actual importance determined post-training using SHAP values*

---

## 3. Target Definition

### 3.1 Fraud Label Definition

#### Ground Truth Source
**Primary Label:** `fraud_label` column in transaction table
- **TRUE (1):** Confirmed fraud by investigation team or customer dispute
- **FALSE (0):** Legitimate transaction (no fraud report)
- **NULL:** Unlabeled (recently occurred, investigation pending)

#### Labeling Process
1. **Automated Signals:**
   - Customer reports fraud via app/website → immediate label
   - Chargeback filed with "fraud" reason → label within 48h
   - Card issuer fraud alert → label within 24h

2. **Manual Investigation:**
   - Flagged by rule-based system → investigator reviews → label assigned
   - Random sampling for quality assurance → retroactive labeling
   - Response time: 1-7 days

3. **Delayed Labels:**
   - 60% of fraud reported within 7 days
   - 30% reported 8-30 days
   - 10% reported 31-90 days
   - Transactions >90 days with no report assumed legitimate (noisy label risk)

#### Label Quality
- **Precision:** ~95% (false fraud reports rare, investigated)
- **Recall:** ~85% (some fraud goes unreported, customer unaware)
- **Noise:** ~5% label error rate (customer mistakes, investigation errors)

### 3.2 Class Distribution

#### Historical Distribution (Training Set)
- **Fraud (Positive):** 25,000 cases (0.5%)
- **Legitimate (Negative):** 4,975,000 cases (99.5%)
- **Total Labeled:** 5,000,000 transactions
- **Unlabeled:** ~45,000,000 transactions (historical data before labeling process)

#### Temporal Distribution
- **Recent Data (0-7 days):** ~40% labeled (fast reports)
- **Medium Age (8-30 days):** ~80% labeled
- **Older Data (31-90 days):** ~95% labeled
- **Historical (>90 days):** ~98% labeled

#### Fraud Type Breakdown
- **Stolen Card:** 40% (physical theft, skimming)
- **Lost Card:** 15% (customer lost card, found by fraudster)
- **Account Takeover:** 25% (credentials compromised, online fraud)
- **Identity Theft:** 10% (new account fraud, synthetic identity)
- **Friendly Fraud:** 5% (customer disputes legitimate purchase)
- **Merchant Fraud:** 5% (merchant collusion, fake transactions)

### 3.3 Target Engineering

#### Binary Classification
- **Primary Task:** Predict fraud probability [0.0, 1.0]
- **Decision:** Threshold-based (optimized for business cost, not 0.5)
- **Output:** fraud_probability, fraud_prediction (binary), risk_score (0-100)

#### Multi-Class Extension (Future)
**Classes:**
1. Legitimate (99.5%)
2. Stolen Card (0.20%)
3. Account Takeover (0.12%)
4. Identity Theft (0.05%)
5. Other Fraud (0.13%)

*Not implemented in v1, reserved for future enhancement*

---

## 4. Pipeline Architecture

### 4.1 Overall Pipeline Flow

```
[Raw Data] → [Cleaning] → [Feature Engineering] → [Encoding] → [Scaling]
    ↓
[Train/Val/Test Split (Temporal)] → [SMOTE (Train Only)] → [Training]
    ↓
[Model Artifacts] → [Inference Pipeline] → [Real-time Scoring] → [Post-processing]
```

### 4.2 Data Cleaning Pipeline

**Stage 1: Validation & Filtering**
1. **Remove duplicates:** Deduplicate by transaction_id (log count)
2. **Data type validation:** Ensure amounts are numeric, timestamps valid
3. **Range validation:** Amount > 0, credit_score in [300, 850]
4. **Remove test transactions:** Filter out merchant_id starting with "TEST_"
5. **Remove system transactions:** Filter out transaction_type = "system_internal"

**Stage 2: Missing Value Handling**
1. **Categorical features:** 
   - payment_method: Missing → "UNKNOWN"
   - card_type: Missing → "NOT_CARD" (indicates non-card payment)
   - merchant_category_code: Missing → "0000"

2. **Numerical features:**
   - latitude/longitude: Missing → 0.0 (equator), create `has_geolocation` binary feature
   - device_id: Missing → "UNKNOWN_DEVICE", create `has_device_info` binary feature
   - customer_avg_transaction_amount: Missing (new customer) → median of all customers

3. **Imputation Strategy:**
   - <5% missing: Median imputation
   - 5-30% missing: Median + missing indicator feature
   - >30% missing: Feature excluded or category-based imputation

**Stage 3: Outlier Treatment**
1. **Statistical outliers:** Winsorize amounts at 99.9th percentile (cap at $50,000)
2. **Impossible values:** Geolocation >90° latitude → NULL
3. **Business outliers:** Transactions >$100K → manual review queue (keep in data)

### 4.3 Feature Engineering Pipeline

**Stage 1: Temporal Features**
1. Extract hour, day_of_week, is_weekend, is_night_time from timestamp
2. Calculate time_since_last_transaction (requires sorting by customer_id, timestamp)
3. Calculate days_since_account_creation
4. Calculate hour_deviation_from_customer_norm (requires customer historical mean)

**Stage 2: Aggregation Features**
1. **Customer aggregations (rolling windows):**
   - Transaction count: 7d, 30d
   - Declined transaction count: 7d
   - Unique merchants: 30d
   - Max transaction amount: 30d
   - Average transaction amount: lifetime

2. **Merchant aggregations:**
   - Fraud rate: 30d
   - Transaction count: 30d
   - Average amount: lifetime
   - Chargeback rate: 30d

3. **Customer-Merchant interaction:**
   - Interaction count: lifetime
   - Days since last interaction

**Stage 3: Interaction Features**
1. Ratio features: amount / customer_avg, amount / merchant_avg
2. Product features: amount * merchant_risk, velocity * amount
3. Binary flags: impossible_travel, high_risk_combination, device_mismatch

**Stage 4: Geospatial Features**
1. Calculate distance_from_home (Haversine formula)
2. Detect impossible_travel (distance / time > 500 mph)
3. Country mismatch flags

### 4.4 Encoding Pipeline

**Categorical Encoding Strategy:**

1. **One-Hot Encoding (low cardinality <10 categories):**
   - transaction_type (4 categories)
   - payment_method (5 categories)
   - day_of_week (7 categories)
   - customer_kyc_status (3 categories)
   - customer_risk_category (4 categories)

2. **Target Encoding (high cardinality >50 categories):**
   - merchant_category_code (~300 categories)
   - device_id (~10K categories)
   - merchant_id (~50K categories)
   - Method: Replace with mean fraud rate, smoothed with global mean
   - Formula: (count * mean_category + alpha * global_mean) / (count + alpha), alpha=10

3. **Ordinal Encoding (inherent order):**
   - customer_risk_category: low=0, medium=1, high=2, critical=3
   - customer_kyc_status: pending=0, verified=1, rejected=2

4. **Cyclical Encoding (circular features):**
   - transaction_hour: sin(2π * hour/24), cos(2π * hour/24)
   - day_of_week: sin(2π * day/7), cos(2π * day/7)

### 4.5 Scaling Pipeline

**Numerical Feature Scaling:**

1. **StandardScaler (z-score normalization):**
   - Applied to: customer_credit_score, merchant_risk_score, merchant_country_risk
   - Formula: (x - mean) / std
   - Reason: These features already interpretable, want to preserve distribution

2. **Log Transform + StandardScaler:**
   - Applied to: transaction_amount, distance_from_home, customer_lifetime_transaction_volume
   - Formula: log1p(x), then standardize
   - Reason: Heavy right skew, log makes more gaussian

3. **MinMaxScaler (0-1 normalization):**
   - Applied to: fraud_rate features (already 0-1 but different scales)
   - Formula: (x - min) / (max - min)
   - Reason: Preserve 0-1 interpretation

4. **No Scaling:**
   - Binary features: Already 0-1
   - Count features: Tree-based models handle raw counts well
   - Ratio features: Already normalized

**Scaling Strategy:**
- **Training:** Fit scaler on training set only, save scaler parameters
- **Validation/Test:** Transform using training set parameters (no leakage)
- **Inference:** Load saved scaler, transform new data

### 4.6 Train/Validation/Test Split

**Temporal Split Strategy:**
- **Training Set:** Months 1-18 (75%)
- **Validation Set:** Months 19-21 (12.5%)
- **Test Set:** Months 22-24 (12.5%)

**Rationale:**
- Temporal split prevents data leakage (future info in training)
- Mimics production scenario (train on past, predict future)
- Validation for hyperparameter tuning
- Test for final unbiased evaluation

**Stratification:**
- Ensure fraud rate consistent across splits (~0.5% each)
- If stratification breaks temporal ordering, prioritize temporal

**Unlabeled Data Handling:**
- Train only on labeled transactions
- Use unlabeled for semi-supervised learning (future enhancement)
- Isolation Forest trained on all data (unsupervised)

### 4.7 Imbalance Handling (Training Only)

**SMOTE (Synthetic Minority Over-sampling Technique):**
- **Applied to:** Training set only (never validation/test)
- **Target ratio:** Upsample fraud to 5% of training set (1:20 instead of 1:200)
- **Method:** Generate synthetic fraud examples by interpolating between nearest neighbors
- **K-neighbors:** 5 (standard)
- **Rationale:** Partial rebalancing (not full 50-50) maintains some real-world distribution

**Class Weights:**
- **Cost-sensitive learning:** Penalize FN 20x more than FP in loss function
- **XGBoost scale_pos_weight:** 20 (FN cost / FP cost)
- **Rationale:** Even after SMOTE, model needs to prioritize fraud recall

**Alternative Strategies (not used):**
- **Random oversampling:** Rejected (overfitting to exact fraud examples)
- **Random undersampling:** Rejected (loses legitimate transaction patterns)
- **ADASYN:** Rejected (SMOTE simpler, equally effective)

### 4.8 Training Pipeline

**XGBoost Training Process:**
1. Load preprocessed training data (SMOTE applied)
2. Define objective: binary:logistic
3. Define eval_metric: auc, aucpr, custom business cost
4. Set hyperparameters (see Model Selection section)
5. Train with early stopping (validation set as eval_set)
6. Save model artifacts, feature names, scaler parameters

**Isolation Forest Training Process:**
1. Load all transactions (labeled + unlabeled)
2. Train unsupervised (no labels needed)
3. Set contamination=0.005 (expected fraud rate)
4. Predict anomaly scores [-1, 1]
5. Save model artifacts

**Training Infrastructure:**
- **Hardware:** AWS EC2 p3.2xlarge (GPU for XGBoost GPU hist)
- **Training time:** ~2 hours (50M transactions)
- **Memory:** 61 GB RAM
- **Storage:** 500 GB SSD (raw data, features, models)

### 4.9 Validation Pipeline

**Hyperparameter Tuning:**
- **Method:** Bayesian Optimization (Optuna framework)
- **Search space:** 50 hyperparameter combinations
- **Objective:** Maximize F-beta score (β=2, weight recall 2x precision)
- **Cross-validation:** None (temporal split sufficient)
- **Time budget:** 10 hours

**Validation Metrics:**
- AUC-ROC, AUC-PR
- Precision, Recall, F1, F-beta
- Business cost metric (see Evaluation section)
- Confusion matrix analysis

**Model Selection Criteria:**
- **Primary:** Business cost (minimize false negatives weighted 20x)
- **Secondary:** AUC-PR (better than AUC-ROC for imbalanced)
- **Tertiary:** Inference latency (<100ms p95)

### 4.10 Inference Pipeline

**Real-time Scoring Flow:**
1. **Input:** Raw transaction JSON from API
2. **Feature extraction:** 
   - Lookup customer/merchant historical features (Redis cache)
   - Calculate temporal features (current timestamp)
   - Calculate interaction features
   - Handle missing values (use inference-time strategy)
3. **Feature encoding:** Apply saved encoders (one-hot, target encoding)
4. **Feature scaling:** Apply saved scalers (standard, log, minmax)
5. **Model scoring:**
   - XGBoost prediction: fraud_prob_xgb
   - Isolation Forest score: anomaly_score_if
   - Ensemble: weighted average (0.7 * xgb + 0.3 * if)
6. **Post-processing:**
   - Convert to fraud_probability [0, 1]
   - Convert to risk_score [0, 100]
   - Apply decision threshold (e.g., 0.85 → BLOCK, 0.50-0.85 → REVIEW, <0.50 → APPROVE)
7. **Output:** JSON response with fraud_probability, risk_score, decision, explanation

**Latency Requirements:**
- **p50:** <50ms
- **p95:** <100ms
- **p99:** <200ms

**Caching Strategy:**
- Customer aggregations cached in Redis (TTL: 1 hour)
- Merchant aggregations cached in Redis (TTL: 6 hours)
- Feature transformers (scalers, encoders) cached in memory

**Batch Scoring:**
- Used for historical analysis, not real-time decisions
- Process entire day's transactions overnight
- Same pipeline as real-time, no caching needed
- Output: fraud scores for reporting/analytics

---

## 5. Model Selection

### 5.1 Why XGBoost (Primary Model)

**Selected:** XGBoost (Extreme Gradient Boosting)

**Rationale:**

1. **Performance on Tabular Data:**
   - State-of-the-art for structured/tabular datasets
   - Consistently wins Kaggle competitions for fraud detection
   - Handles mixed data types (numerical, categorical) naturally

2. **Handles Class Imbalance:**
   - Built-in class weighting (scale_pos_weight parameter)
   - Works well with SMOTE
   - Supports custom loss functions for cost-sensitive learning

3. **Feature Interactions:**
   - Automatically learns complex feature interactions (non-linear relationships)
   - No manual feature crossing needed
   - Captures customer_amount × merchant_risk type patterns

4. **Robustness:**
   - Handles missing values internally (directional splitting)
   - Resistant to outliers (tree-based, not distance-based)
   - Less prone to overfitting than single decision trees (regularization)

5. **Speed:**
   - Fast training with GPU support (histogram-based algorithm)
   - Fast inference (<10ms per prediction)
   - Scales to 50M+ transactions

6. **Interpretability:**
   - Feature importance scores (gain, cover, frequency)
   - SHAP values supported natively
   - Tree visualization for auditing

7. **Industry Proven:**
   - Used by PayPal, Stripe, Square for fraud detection
   - Mature library, active development
   - Strong community support

**Hyperparameters (Optimized via Bayesian Search):**
```
objective: binary:logistic
eval_metric: aucpr
max_depth: 8 (prevent overfitting)
learning_rate: 0.05 (slow learning, better generalization)
n_estimators: 500 (with early stopping)
min_child_weight: 50 (prevent overfitting on rare cases)
subsample: 0.8 (row sampling for regularization)
colsample_bytree: 0.8 (column sampling)
scale_pos_weight: 20 (FN 20x more expensive than FP)
gamma: 0.1 (minimum loss reduction for split)
reg_alpha: 0.1 (L1 regularization)
reg_lambda: 1.0 (L2 regularization)
tree_method: hist (histogram-based, faster)
device: cuda (GPU acceleration)
```

### 5.2 Why Isolation Forest (Secondary Model)

**Selected:** Isolation Forest (Unsupervised Anomaly Detection)

**Rationale:**

1. **Novel Fraud Detection:**
   - Detects anomalies without labels (finds new fraud patterns)
   - Catches zero-day fraud tactics not seen in training
   - Complements XGBoost (which learns from past fraud)

2. **Unsupervised:**
   - Doesn't require fraud labels (uses all 50M transactions)
   - Not biased by label delay (recent unlabeled data used)
   - Finds statistical outliers in feature space

3. **Speed:**
   - Fast training (random sampling)
   - Fast inference (tree-based like XGBoost)
   - Scales to large datasets

4. **Intuition:**
   - Fraud is rare and different (anomalous)
   - Isolating anomalies requires fewer tree splits
   - Anomaly score = how "easy" to isolate transaction

5. **Ensemble Benefit:**
   - XGBoost: Precision-focused (low FP)
   - Isolation Forest: Recall-focused (catch novel fraud)
   - Combined: Better precision-recall tradeoff

**Hyperparameters:**
```
n_estimators: 200 (number of isolation trees)
contamination: 0.005 (expected fraud rate 0.5%)
max_samples: 50000 (subsample for speed, sufficient for patterns)
max_features: 0.8 (column sampling)
bootstrap: False (use full sample set)
random_state: 42 (reproducibility)
```

**Ensemble Strategy:**
```
final_score = 0.7 * xgboost_prob + 0.3 * isolation_forest_anomaly_score_normalized
```
- XGBoost weighted higher (more accurate on known fraud)
- Isolation Forest adds recall for novel patterns
- Weights tuned on validation set

### 5.3 Why NOT Deep Learning

**Rejected Approaches:**

**1. Deep Neural Networks (DNNs)**

**Why NOT:**
- **Insufficient data:** Deep learning requires 10M+ labeled examples (we have 25K fraud cases)
- **Overfitting risk:** DNNs overfit easily on imbalanced data
- **Interpretability:** Black box, hard to explain to regulators/customers
- **Training time:** Hours to days (vs minutes for XGBoost)
- **Inference latency:** 20-50ms (vs <10ms for XGBoost)
- **Hyperparameter sensitivity:** Requires extensive tuning
- **Not proven better:** No evidence DNNs outperform XGBoost on fraud (tabular data)

**When it WOULD make sense:**
- Image-based fraud (fake IDs, document forgery)
- Sequential fraud patterns (RNN/LSTM for transaction sequences)
- Unstructured text (fraud in product descriptions, emails)

**2. Autoencoders (Unsupervised)**

**Why NOT:**
- **Reconstruction error unreliable:** Legitimate outliers also have high error
- **No class weights:** Can't encode FN cost preference
- **Latency:** 30-100ms (too slow for real-time)
- **Interpretability:** Latent space not interpretable
- **Isolation Forest better:** Simpler, faster, equally effective for anomaly detection

**3. Transformers / Attention Models**

**Why NOT:**
- **Sequential data not required:** Transactions are independent (not text/time series)
- **Massive computational cost:** Training requires GPUs for days
- **Inference latency:** 100-500ms (unacceptable)
- **Overkill:** Designed for language/vision, not tabular fraud

### 5.4 Why NOT Random Forest

**Rejected:** Random Forest (Ensemble of Decision Trees)

**Why NOT:**
- **XGBoost strictly better:** Gradient boosting > bagging for fraud
- **Slower training:** RF trains full trees, XGBoost uses boosting (faster convergence)
- **Lower accuracy:** XGBoost wins in benchmarks (5-10% better AUC-PR)
- **Less regularization:** RF prone to overfitting on imbalanced data
- **No class weighting:** Harder to implement cost-sensitive learning

**When RF WOULD make sense:**
- High variance models (XGBoost overfitting)
- Parallel training required (RF fully parallelizable, XGBoost sequential)
- Extreme interpretability (single tree easier than boosted ensemble)

**Note:** Random Forest considered as fallback if XGBoost overfits validation set.

### 5.5 Why NOT Neural Networks (Specific Architectures)

**1. Convolutional Neural Networks (CNNs)**
- **Why NOT:** No spatial structure in tabular fraud data (CNNs for images)
- **Use case:** Would apply if processing transaction receipt images

**2. Recurrent Neural Networks (RNNs/LSTMs)**
- **Why NOT:** Transactions treated as independent events, not sequences
- **Possible future:** Could model customer transaction sequence (fraud trajectory)
- **Why still NOT:** XGBoost with temporal aggregation features sufficient

**3. Graph Neural Networks (GNNs)**
- **Why NOT:** No explicit graph structure in current data model
- **Possible future:** Customer-merchant-device network could use GNN
- **Why still NOT:** Feature engineering captures relationships without GNN complexity

### 5.6 Why NOT Logistic Regression

**Rejected:** Logistic Regression (Linear Model)

**Why NOT:**
- **Linear assumption:** Fraud patterns highly non-linear (feature interactions critical)
- **Feature engineering burden:** Would need manual feature crossing (amount × risk)
- **Lower accuracy:** 20-30% worse AUC-PR than XGBoost in benchmarks
- **Interpretability not needed:** SHAP provides better explanations than coefficients

**When LR WOULD make sense:**
- Regulatory requirement for "simple, explainable" model (EU GDPR "right to explanation")
- Baseline model (starting point before tree-based models)
- Real-time coefficient updates (online learning easier with linear models)

**Note:** Logistic Regression used as baseline to measure XGBoost improvement.

### 5.7 Why NOT Support Vector Machines (SVM)

**Rejected:** SVM (Kernel-based Classifier)

**Why NOT:**
- **Scalability:** SVM O(n²-n³) training time, infeasible for 50M transactions
- **Memory:** Kernel matrix requires massive RAM
- **Inference latency:** 50-200ms (support vectors in memory)
- **Hyperparameter sensitivity:** Kernel selection, gamma tuning critical
- **No probabilistic output:** Needs Platt scaling for probabilities

### 5.8 Why NOT Naive Bayes

**Rejected:** Naive Bayes (Probabilistic Classifier)

**Why NOT:**
- **Feature independence assumption:** Violated (amount and merchant_risk correlated)
- **Continuous features:** Requires distributional assumptions (Gaussian)
- **Lower accuracy:** 30-40% worse than XGBoost
- **No feature interactions:** Linear decision boundaries

### 5.9 Model Selection Summary

| Model | Accuracy | Speed | Interpretability | Scalability | Selected? |
|-------|----------|-------|------------------|-------------|-----------|
| **XGBoost** | ★★★★★ | ★★★★★ | ★★★★☆ | ★★★★★ | ✅ Primary |
| **Isolation Forest** | ★★★☆☆ | ★★★★★ | ★★★☆☆ | ★★★★★ | ✅ Secondary |
| Deep Neural Network | ★★☆☆☆ | ★★☆☆☆ | ★☆☆☆☆ | ★★★☆☆ | ❌ |
| Random Forest | ★★★★☆ | ★★★☆☆ | ★★★★☆ | ★★★★☆ | ❌ |
| Logistic Regression | ★★☆☆☆ | ★★★★★ | ★★★★★ | ★★★★★ | ❌ |
| SVM | ★★★☆☆ | ★☆☆☆☆ | ★★☆☆☆ | ★☆☆☆☆ | ❌ |
| Naive Bayes | ★☆☆☆☆ | ★★★★★ | ★★★★★ | ★★★★★ | ❌ |

---

## 6. Evaluation Strategy

### 6.1 Evaluation Metrics

**Metric 1: Precision**

**Definition:** Of predicted fraud cases, what % are actually fraud?
```
Precision = TP / (TP + FP)
```

**Why Used:**
- Measures false positive rate impact
- High precision = fewer legitimate transactions flagged
- Reduces customer service load and customer frustration

**Target:** ≥85% precision
**Business Impact:** 85% precision means 15% of fraud alerts are false (acceptable)

**Metric 2: Recall (Sensitivity)**

**Definition:** Of actual fraud cases, what % are caught?
```
Recall = TP / (TP + FN)
```

**Why Used:**
- Measures fraud detection coverage
- High recall = fewer frauds slip through
- Directly impacts financial losses

**Target:** ≥75% recall
**Business Impact:** 75% recall means catching 3 out of 4 fraud cases ($375 saved per $500 fraud)

**Metric 3: F-beta Score (β=2)**

**Definition:** Weighted harmonic mean of precision and recall
```
F-beta = (1 + β²) × (Precision × Recall) / (β² × Precision + Recall)
```
β=2 weights recall 2x more than precision

**Why Used:**
- Single metric balancing precision and recall
- β=2 prioritizes recall (fraud costs more than false positives)
- Used for model selection during hyperparameter tuning

**Target:** ≥0.80 F2 score

**Metric 4: AUC-ROC (Area Under ROC Curve)**

**Definition:** Probability model ranks random fraud higher than random legitimate
```
AUC-ROC = Integral of (TPR vs FPR curve)
TPR = Recall, FPR = FP / (FP + TN)
```

**Why Used:**
- Threshold-independent (evaluates ranking, not classification)
- Standard metric for binary classifiers
- Easy to compare across models

**Target:** ≥0.95 AUC-ROC
**Limitation:** Optimistic on imbalanced data (high TN inflates score)

**Metric 5: AUC-PR (Area Under Precision-Recall Curve)**

**Definition:** Precision vs Recall at all thresholds
```
AUC-PR = Integral of (Precision vs Recall curve)
```

**Why Used:**
- **PRIMARY METRIC** for imbalanced data
- More informative than AUC-ROC when fraud rare
- Focuses on positive class performance

**Target:** ≥0.70 AUC-PR
**Why better:** Doesn't inflate from large TN count

**Metric 6: Business Cost Metric**

**Definition:** Expected cost per transaction
```
Cost = (FN × $500) + (FP × $25)
```

**Why Used:**
- **ULTIMATE OBJECTIVE** - Minimize business losses
- Directly translates model performance to dollars
- Guides threshold selection (optimize for cost, not accuracy)

**Target:** <$5 expected cost per transaction (baseline: $10 with no model)
**Business Impact:** 50% cost reduction = $5M annual savings (1M transactions/day)

**Metric 7: Confusion Matrix**

**Definition:** 2×2 table of predictions vs actuals
```
                Predicted Fraud    Predicted Legitimate
Actual Fraud         TP                    FN
Actual Legitimate    FP                    TN
```

**Why Used:**
- Granular view of error types
- Identifies if model biased toward FP or FN
- Used for threshold tuning

**Metric 8: Classification Report**

**Definition:** Per-class precision, recall, F1
**Why Used:** Detailed performance breakdown for both classes

### 6.2 Threshold Selection Strategy

**Challenge:** Default threshold (0.5) is arbitrary and suboptimal for imbalanced data

**Approach:** Cost-based threshold optimization

**Method:**
1. Generate predictions on validation set (probabilities, not binary)
2. For each threshold t ∈ [0.01, 0.99] (step 0.01):
   - Apply threshold: y_pred = (prob >= t)
   - Calculate confusion matrix
   - Calculate business cost: FN×$500 + FP×$25
3. Select threshold minimizing business cost

**Expected Optimal Threshold:** ~0.20-0.35 (lower than 0.5 due to cost asymmetry)

**Decision Rules:**
- prob ≥ 0.85: BLOCK transaction (high confidence fraud)
- 0.35 ≤ prob < 0.85: REVIEW (manual investigation)
- prob < 0.35: APPROVE (low risk)

**Rationale:**
- Lower threshold increases recall (catch more fraud) at cost of precision
- Three-tier system balances automation and human review
- REVIEW queue handles ambiguous cases (40-50% of fraud predictions)

### 6.3 Cost-Sensitive Evaluation

**Cost Matrix:**
```
               Predict Fraud    Predict Legitimate
True Fraud         $0                $500 (FN cost)
True Legitimate    $25 (FP cost)     $0
```

**Cost Calculation:**
```
Total Cost = (FN × $500) + (FP × $25)
Average Cost per Transaction = Total Cost / Total Transactions
```

**Example Scenarios:**

**Scenario 1: High Precision, Low Recall**
- TP=150, FN=50, FP=10, TN=99,790
- Precision=93.8%, Recall=75%, F1=83.3%
- Cost = (50 × $500) + (10 × $25) = $25,250
- Avg Cost = $0.25 per transaction
- **Interpretation:** Misses 25% of fraud but very few false positives

**Scenario 2: High Recall, Low Precision**
- TP=180, FN=20, FP=200, TN=99,600
- Precision=47.4%, Recall=90%, F1=62.2%
- Cost = (20 × $500) + (200 × $25) = $15,000
- Avg Cost = $0.15 per transaction
- **Interpretation:** Catches most fraud but many false positives

**Scenario 3: Balanced (Target)**
- TP=170, FN=30, FP=30, TN=99,770
- Precision=85%, Recall=85%, F1=85%
- Cost = (30 × $500) + (30 × $25) = $15,750
- Avg Cost = $0.16 per transaction
- **Interpretation:** Optimal cost-effectiveness

**Threshold Impact:**
| Threshold | Precision | Recall | F1 | Cost/Txn | Decision |
|-----------|-----------|--------|----|-----------| ---------|
| 0.10 | 60% | 95% | 73.8% | $0.20 | Too many FP |
| 0.20 | 75% | 90% | 81.8% | $0.16 | Good |
| 0.30 | 85% | 85% | 85.0% | $0.16 | **Optimal** |
| 0.50 | 92% | 65% | 76.3% | $0.20 | Miss too much fraud |
| 0.70 | 96% | 45% | 61.1% | $0.28 | Miss way too much |

### 6.4 Evaluation on Test Set

**Holdout Test Set:** Month 22-24 (12.5% of data, ~6M transactions)

**Test Protocol:**
1. **No retraining:** Models frozen after validation tuning
2. **Single evaluation:** Test set used once (prevent overfitting)
3. **Threshold fixed:** Use validation-optimized threshold (no tuning on test)
4. **Temporal realism:** Test set is future data (mimics production)
5. **Report all metrics:** Precision, recall, F1, F-beta, AUC-ROC, AUC-PR, cost

**Success Criteria (Test Set):**
- AUC-PR ≥ 0.70
- Precision ≥ 85%
- Recall ≥ 75%
- F-beta (β=2) ≥ 0.80
- Business cost < $0.20 per transaction

**Failure Scenarios:**
- Test metrics significantly worse than validation (>10% drop) → overfitting, retrain
- Temporal drift detected (fraud patterns changed) → retrain on recent data
- Business cost exceeds $0.30 → model not cost-effective, revert to rules

### 6.5 Error Analysis

**Post-Evaluation Analysis:**

**1. False Positive Analysis (Type I Error)**
- **Sample:** 100 random FP cases
- **Questions:**
  - What legitimate patterns look like fraud?
  - Are there customer segments over-flagged?
  - Which features drive FP predictions?
- **Action:** Add features to distinguish these cases or adjust threshold

**2. False Negative Analysis (Type II Error)**
- **Sample:** All FN cases (critical, <30 expected)
- **Questions:**
  - What fraud patterns are missed?
  - Are these novel fraud types?
  - Which features failed to signal fraud?
- **Action:** Add features, collect more fraud examples, adjust class weights

**3. Temporal Analysis**
- **By Week:** Plot precision/recall over time (detect drift)
- **By Month:** Aggregate metrics per month
- **Seasonality:** Check if holidays, weekends affect performance

**4. Segment Analysis**
- **By Amount Bracket:** <$100, $100-$1K, $1K-$10K, >$10K
- **By Customer Age:** New (<30d), Medium (30-365d), Old (>365d)
- **By Transaction Type:** Purchase, withdrawal, transfer
- **By Geography:** Domestic vs international

**5. Feature Importance Drift**
- Compare feature importance on test vs training
- Check if critical features lost predictive power

---

## 7. Explainability

### 7.1 SHAP (SHapley Additive exPlanations)

**What is SHAP:**
- Game-theory approach to explain model predictions
- Assigns each feature a contribution score (positive or negative)
- Sum of all SHAP values = (prediction - baseline)
- Model-agnostic but optimized for tree models (TreeSHAP)

**Why SHAP:**
- **Theoretically sound:** Based on Shapley values (fair attribution)
- **Consistent:** If feature helps, SHAP value is positive
- **Local + Global:** Explains both individual predictions and overall model
- **Regulatory compliance:** Satisfies GDPR "right to explanation"
- **Customer trust:** Can show customers why transaction flagged

### 7.2 Global Explainability

**Purpose:** Understand overall model behavior across all transactions

**Technique 1: Feature Importance (SHAP Summary Plot)**
- **Visualization:** Beeswarm plot (feature importance + direction + density)
- **Interpretation:** 
  - Y-axis: Features ranked by importance
  - X-axis: SHAP value (impact on prediction)
  - Color: Feature value (red=high, blue=low)
- **Example Insights:**
  - "High impossible_travel_flag increases fraud probability"
  - "High customer_historical_fraud_count is strongest predictor"
  - "Low customer_age_days increases fraud risk"

**Technique 2: Feature Dependence Plots**
- **Visualization:** Scatter plot (feature value vs SHAP value)
- **Interpretation:** Shows non-linear relationships
- **Example:**
  - transaction_amount: Low amounts (<$50) have near-zero impact, high amounts (>$1000) have high positive SHAP values (U-shaped)
  - customer_age_days: Exponential decay (new accounts high risk, old accounts low risk)

**Technique 3: Feature Interaction**
- **Visualization:** Dependence plot colored by secondary feature
- **Interpretation:** Shows how features interact
- **Example:**
  - amount × merchant_risk: High amount is only risky if merchant_risk also high

**Deliverable:** Global Explainability Dashboard
- Feature importance ranking with SHAP values
- Top 20 features visualized
- Updated monthly with production data

### 7.3 Local Explainability

**Purpose:** Explain why a specific transaction was flagged as fraud

**Technique: SHAP Waterfall Plot**
- **Visualization:** Bar chart showing contribution of each feature
- **Components:**
  - Base value: Average model prediction (0.005 = 0.5% fraud rate)
  - Red bars: Features increasing fraud probability
  - Blue bars: Features decreasing fraud probability
  - Final value: Actual prediction for this transaction

**Example: Transaction Flagged as Fraud (prob=0.92)**

```
Base value: 0.005

+ impossible_travel_flag = 1        +0.35
+ customer_historical_fraud_count = 2  +0.25
+ amount_to_customer_avg_ratio = 50    +0.15
+ merchant_fraud_rate_30d = 0.08       +0.10
+ is_international = 1                  +0.08
+ customer_age_days = 5                 +0.06
- customer_credit_score = 780           -0.02
- merchant_is_verified = 1              -0.01

Final prediction: 0.92 (HIGH FRAUD RISK)
```

**Interpretation for Fraud Analyst:**
- "Transaction flagged because: impossible travel detected (card in NYC 2 hours ago, now in London), customer has 2 prior fraud cases, amount 50x higher than usual, merchant has 8% fraud rate, international transaction, very new account. Credit score and verified merchant slightly reduce risk but not enough."

**Deliverable:** Per-Transaction Explanation API
- Endpoint: `/v1/predictions/{transaction_id}/explain`
- Response: JSON with top 10 SHAP values and plain-English explanation
- Used by fraud investigators and customer service

### 7.4 Business Explanation

**Challenge:** SHAP values are technical; business users need simple explanations

**Solution:** Rule-based explanation generator

**Template:**
```
"This transaction was flagged as [HIGH/MEDIUM/LOW] risk because:

Primary Factors:
- [Top reason with business context]
- [Second reason with business context]
- [Third reason with business context]

Mitigating Factors:
- [Reason reducing risk, if any]

Recommendation: [BLOCK/REVIEW/APPROVE]
Confidence: [0-100]%
```

**Example Output:**

**High Risk Transaction:**
```
Risk Score: 92/100 (HIGH RISK - BLOCKED)

This transaction was flagged as HIGH risk because:

Primary Factors:
- Impossible travel detected: Card used in New York 2 hours ago,
  now in London (physically impossible)
- Customer has history of fraud: 2 previous fraud reports in past 6 months
- Unusual purchase amount: $5,000 transaction when customer typically 
  spends $100 (50x normal)
- High-risk merchant: This merchant has 8% fraud rate (16x platform average)

Mitigating Factors:
- Customer has good credit score (780)
- Merchant is verified

Recommendation: BLOCK transaction and contact customer
Confidence: 92%
Next Steps: Fraud investigator will review within 1 hour
```

**Medium Risk Transaction:**
```
Risk Score: 68/100 (MEDIUM RISK - REVIEW)

This transaction was flagged for manual review because:

Primary Factors:
- New merchant: First time customer is purchasing from this merchant
- International transaction: Customer is in USA, merchant in China
- Large amount: $1,200 purchase (12x customer average)

Mitigating Factors:
- Established account: Customer has been active for 3 years
- No fraud history: Customer has never reported fraud
- Normal transaction time: Purchase made during customer's usual hours

Recommendation: Manual review by fraud analyst
Confidence: 68%
Expected Review Time: 15 minutes
```

**Mapping SHAP to Business Language:**

| Feature | SHAP Interpretation | Business Explanation |
|---------|---------------------|----------------------|
| impossible_travel_flag=1 | +0.35 | "Impossible travel detected (physical card cannot teleport)" |
| customer_historical_fraud_count=2 | +0.25 | "Customer has 2 prior fraud cases (repeat victim)" |
| amount_to_customer_avg_ratio=50 | +0.15 | "Purchase $5,000 vs usual $100 (50x larger than normal)" |
| merchant_fraud_rate_30d=0.08 | +0.10 | "Merchant has 8% fraud rate (16x platform average of 0.5%)" |
| is_international=1 | +0.08 | "Cross-border transaction (higher risk)" |
| customer_age_days=5 | +0.06 | "Very new account (only 5 days old, common in fraud)" |

### 7.5 Explainability for Regulators

**Regulatory Requirements (GDPR Article 22):**
- Right to explanation for automated decisions
- Must be "meaningful information about the logic involved"
- Must enable customers to challenge decisions

**Our Approach:**

**1. Model Documentation:**
- Algorithm description (XGBoost gradient boosting)
- Feature list with definitions (all 47 features documented)
- Training data sources (transaction database)
- Performance metrics (precision, recall, AUC)

**2. Per-Decision Explanation:**
- SHAP waterfall plot (visual)
- Plain-English summary (non-technical)
- Top 5 features contributing to decision
- Contact information for human review

**3. Appeal Process:**
- Customer can request manual review
- Human investigator reviews with SHAP explanation
- Decision can be overridden (model is not final authority)
- Overrides logged and used for model improvement

**4. Audit Trail:**
- Every prediction logged with timestamp, features, model version
- Reproducible (can regenerate prediction with same inputs)
- Retained for 7 years (regulatory requirement)

---

## 8. Monitoring Strategy

### 8.1 Data Drift Detection

**What is Data Drift:**
- Input feature distributions change over time
- Example: COVID-19 caused shift to online transactions (is_online distribution changed)
- Model trained on old distribution may underperform on new distribution

**Monitoring Approach:**

**1. Feature Distribution Monitoring**
- **Metric:** Population Stability Index (PSI)
- **Formula:** PSI = Σ (actual% - expected%) × ln(actual% / expected%)
- **Threshold:** PSI > 0.2 indicates significant drift
- **Frequency:** Daily
- **Action:** PSI > 0.2 for 3 consecutive days → investigate, consider retraining

**2. Numerical Feature Drift**
- **Metrics:** Mean, median, std dev, min, max
- **Comparison:** Production vs training statistics
- **Threshold:** >20% change in mean or >30% change in std dev
- **Example:** transaction_amount mean shifts from $250 to $350 (inflation, behavioral change)

**3. Categorical Feature Drift**
- **Metric:** Chi-squared test (distribution similarity)
- **Threshold:** p-value < 0.05 indicates significant drift
- **Example:** payment_method distribution shifts (new wallet adoption)

**4. Correlation Drift**
- **Metric:** Correlation matrix comparison (training vs production)
- **Threshold:** Correlation change >0.3 for critical feature pairs
- **Example:** amount × merchant_risk correlation weakens (fraudsters adapt)

**Monitored Features (Priority):**
1. transaction_amount (HIGH)
2. customer_age_days (HIGH)
3. merchant_fraud_rate_30d (CRITICAL)
4. is_international (MEDIUM)
5. payment_method distribution (MEDIUM)

### 8.2 Concept Drift Detection

**What is Concept Drift:**
- Relationship between features and target changes
- Example: Fraudsters adapt tactics; high-amount transactions no longer predictive
- More severe than data drift (requires retraining, not just recalibration)

**Monitoring Approach:**

**1. Performance Degradation**
- **Metrics:** Precision, recall, F1, AUC-PR (on confirmed labels)
- **Comparison:** Production vs test set
- **Threshold:** >10% drop in any metric
- **Frequency:** Weekly (after labels arrive)
- **Challenge:** Label delay (need to wait 7-30 days for ground truth)

**2. Proxy Metrics (Real-time)**
- **Chargeback rate:** Fraud cases result in chargebacks (30-60 day lag)
- **Customer fraud reports:** Direct feedback (0-7 day lag)
- **Threshold:** Chargeback rate increases >50% week-over-week
- **Action:** Emergency investigation, possible model rollback

**3. Prediction Confidence**
- **Metric:** Average prediction probability
- **Baseline:** Mean prob ~0.05 (given 0.5% fraud rate + false positives)
- **Threshold:** Mean prob drops to <0.03 or rises to >0.10
- **Interpretation:** Model becoming too uncertain or too confident (miscalibrated)

**4. Seasonal Adjustment**
- **Challenge:** Fraud rates vary by season (holidays, tax season)
- **Approach:** Compare current week to same week last year (not last week)
- **Example:** Black Friday has 3x fraud rate; comparing to previous week false alarm

### 8.3 Prediction Drift Detection

**What is Prediction Drift:**
- Model outputs change even though inputs same
- Rare (only happens if model/pipeline changes)
- Can indicate deployment bug or model corruption

**Monitoring Approach:**

**1. Prediction Distribution**
- **Metric:** Histogram of fraud probabilities
- **Baseline:** Training set prediction distribution
- **Threshold:** KL-divergence > 0.5
- **Frequency:** Hourly
- **Action:** KL-div spike → immediate investigation, possible rollback

**2. Decision Distribution**
- **Metric:** % APPROVE / % REVIEW / % BLOCK
- **Baseline:** Expected ~95% APPROVE, ~4% REVIEW, ~1% BLOCK
- **Threshold:** >20% change in any category
- **Example:** Suddenly 10% BLOCK → model bug, kill switch activated

**3. Score Calibration**
- **Metric:** Predicted probability vs actual fraud rate (calibration curve)
- **Method:** Bin predictions [0-0.1, 0.1-0.2, ..., 0.9-1.0], compare pred vs actual
- **Expected:** pred=0.5 → actual~0.5, pred=0.8 → actual~0.8 (well-calibrated)
- **Threshold:** Calibration error >0.15
- **Frequency:** Monthly (requires labeled data)

### 8.4 Feature Drift Monitoring

**Per-Feature Tracking:**

**1. Missing Value Rate**
- **Metric:** % NULL per feature
- **Baseline:** Training set missing rates
- **Threshold:** >50% increase in missing rate
- **Example:** device_id suddenly 50% NULL → data pipeline issue

**2. Out-of-Range Values**
- **Metric:** % values outside training range
- **Threshold:** >5% of values OOR
- **Example:** transaction_amount >$100K (training max $50K) → investigate

**3. New Categories**
- **Metric:** Count of unseen category values
- **Example:** New payment_method "buy_now_pay_later" (not in training)
- **Action:** Add to encoder, retrain if significant volume

**4. Aggregation Feature Staleness**
- **Metric:** Time since feature cache update
- **Threshold:** >24 hours stale (cache TTL exceeded)
- **Action:** Force cache refresh, investigate Redis issue

### 8.5 Latency Monitoring

**Inference Latency SLAs:**
- **p50 < 50ms:** Median user experience
- **p95 < 100ms:** 95% of users get sub-100ms response
- **p99 < 200ms:** Catch outliers, prevent timeouts

**Monitoring:**
- **Metric:** End-to-end prediction latency (API receive to response)
- **Breakdown:**
  - Feature extraction: 20ms (database + Redis)
  - Preprocessing: 10ms (encoding, scaling)
  - Model inference: 15ms (XGBoost + Isolation Forest)
  - Post-processing: 5ms (threshold, explanation)
- **Alerting:** p95 > 150ms for 5 minutes → page on-call engineer

**Throughput Monitoring:**
- **Metric:** Predictions per second (PPS)
- **Baseline:** 1,000 PPS (70K transactions/day = ~1 per second avg, 1000 PPS peak)
- **Capacity:** 5,000 PPS (5x peak capacity)
- **Alerting:** PPS > 4,000 (80% capacity) → scale up

### 8.6 Model Quality Metrics (Production)

**Daily Metrics (Leading Indicators):**
1. **Fraud flag rate:** % transactions flagged (expect ~5%)
2. **Block rate:** % transactions auto-blocked (expect ~1%)
3. **Review queue size:** Transactions pending manual review (expect ~3K/day)
4. **Average fraud score:** Mean prediction probability (expect ~0.05)

**Weekly Metrics (Lagging Indicators, after labels arrive):**
1. **Precision:** Of flagged transactions, % actually fraud (target ≥85%)
2. **Recall:** Of actual fraud, % caught (target ≥75%)
3. **F-beta score:** Weighted precision-recall (target ≥0.80)
4. **AUC-PR:** Ranking quality (target ≥0.70)
5. **Business cost:** Avg cost per transaction (target <$0.20)

**Monthly Metrics (Strategic):**
1. **Fraud loss prevented:** Estimated $ fraud caught (TP × avg fraud amount)
2. **False positive cost:** FP × $25 investigation cost
3. **Net savings:** Fraud prevented - FP cost - operational overhead
4. **Customer satisfaction:** NPS impact from false positive friction

### 8.7 Alerting Strategy

**Critical Alerts (Page On-Call, 24/7):**
1. Model unavailable (503 errors) → 5 minutes
2. Latency p95 > 200ms → 5 minutes
3. Prediction drift (KL-div > 1.0) → immediate
4. Zero fraud predictions for 1 hour (model frozen?) → immediate

**High Priority Alerts (Slack, Business Hours):**
1. Precision drops >15% → daily check
2. Recall drops >15% → daily check
3. Data drift PSI > 0.3 → daily check
4. Feature missing rate >20% → hourly

**Medium Priority Alerts (Email, Weekly):**
1. AUC-PR drops 5-10%
2. Data drift PSI 0.2-0.3
3. Calibration error >0.10

### 8.8 Retraining Strategy

**When to Retrain:**

**1. Scheduled Retraining (Proactive)**
- **Frequency:** Monthly
- **Rationale:** Capture gradual drift, new fraud patterns
- **Process:** Train on last 6 months data, validate on last 1 month
- **Approval:** ML team reviews metrics, product owner approves deployment

**2. Performance-Triggered Retraining (Reactive)**
- **Trigger:** Precision <80% OR Recall <70% for 2 consecutive weeks
- **Rationale:** Model degraded, urgent update needed
- **Process:** Emergency training on last 3 months, fast-track validation
- **Approval:** On-call ML engineer can deploy after validation check

**3. Drift-Triggered Retraining (Reactive)**
- **Trigger:** Data drift PSI >0.3 for 7 consecutive days
- **Rationale:** Input distribution shifted significantly
- **Process:** Analyze drift source, retrain on recent data
- **Approval:** ML team + data engineering review

**4. Business-Triggered Retraining (Strategic)**
- **Trigger:** New fraud pattern identified by fraud team
- **Rationale:** Known threat not captured by model
- **Process:** Collect labeled examples, focused retraining
- **Example:** New account takeover tactic using deepfake IDs

**Who Approves Deployment:**
- **Scheduled:** Product Owner + ML Lead (2 approvals)
- **Performance/Drift:** ML On-Call Engineer (1 approval, documented)
- **Business:** Product Owner + Risk Management (2 approvals)

**Retraining Process:**
1. Extract new labeled data (last N months)
2. Run full preprocessing pipeline
3. Train XGBoost + Isolation Forest
4. Validate on holdout set (last 2 weeks)
5. Compare metrics to current production model
6. If improved (or not degraded), deploy via canary
7. Monitor for 48 hours, full rollout if stable

---

## 9. Risk Management

### 9.1 Data Leakage Risks

**Risk 1: Temporal Leakage (HIGH RISK)**

**Description:** Using future information to predict past events
**Example:**
- merchant_fraud_rate_30d includes fraud cases reported after transaction
- Inflates training performance, fails in production

**Mitigation:**
- Point-in-time feature calculation (use only data available at transaction time)
- Temporal split (train on past, validate on future)
- Feature engineering audit (check each aggregation for leakage)

**Risk 2: Target Leakage (CRITICAL RISK)**

**Description:** Feature is proxy for target (fraud_label)
**Example:**
- is_chargedback feature (100% correlated with fraud)
- transaction_status='reversed' (fraud cases get reversed)

**Mitigation:**
- Feature review checklist: "Would this feature be available in production?"
- Exclude post-transaction features (chargeback, reversal, investigation status)
- Use only pre-transaction and concurrent features

**Risk 3: Training-Serving Skew**

**Description:** Feature calculation differs in training vs production
**Example:**
- Training: customer_avg_amount computed on all history
- Production: customer_avg_amount computed on last 90 days (cache TTL)
- Model sees different feature distributions

**Mitigation:**
- Use same code for training and production (shared library)
- Integration tests comparing training vs serving features
- Schema validation (type, range checks)

### 9.2 Concept Drift Risks

**Risk 1: Adversarial Adaptation (HIGH RISK)**

**Description:** Fraudsters learn model behavior and adapt tactics
**Example:**
- Model flags large amounts → fraudsters make many small transactions
- Model flags impossible travel → fraudsters use VPNs to mask location

**Mitigation:**
- Frequent retraining (monthly) to adapt to new tactics
- Ensemble with unsupervised model (Isolation Forest catches novel patterns)
- Rule-based alerts for known patterns (don't rely solely on ML)
- Keep model details confidential (don't expose decision logic)

**Risk 2: Seasonal Drift (MEDIUM RISK)**

**Description:** Fraud patterns vary by season
**Example:**
- Black Friday: 3x transaction volume, 2x fraud rate
- Tax season: Refund fraud spikes
- Model trained on Q1 underperforms in Q4

**Mitigation:**
- Train on full year of data (capture all seasons)
- Add month/quarter features (seasonal signal)
- Monitor performance by season, retrain if needed

**Risk 3: External Shocks (LOW PROBABILITY, HIGH IMPACT)**

**Description:** Unexpected events change behavior drastically
**Example:**
- COVID-19: Shift to online shopping, new fraud tactics
- Data breach: Massive spike in account takeover
- New payment method: Buy-now-pay-later (not in training data)

**Mitigation:**
- Emergency retraining capability (24-hour turnaround)
- Manual override system (disable model, use rules temporarily)
- Diverse training data (multiple years, regions, transaction types)

### 9.3 Label Delay Risks

**Risk 1: Training on Stale Labels (HIGH RISK)**

**Description:** Recent fraud not yet reported, model trains on incomplete labels
**Example:**
- Last 30 days of data: only 40% fraud reported
- Model learns "recent transactions are legitimate" (false pattern)

**Mitigation:**
- Exclude last 90 days from training (wait for labels to stabilize)
- Label confidence weighting (recent labels weighted lower)
- Online learning (update model as new labels arrive)

**Risk 2: Label Quality Degradation (MEDIUM RISK)**

**Description:** Old fraud cases assumed legitimate (no report after 90 days)
**Example:**
- Customer never checked statement, fraud went unnoticed
- Noisy negative labels (some fraud mislabeled as legitimate)

**Mitigation:**
- Random sampling for manual review (QA labeling process)
- Anomaly detection on "legitimate" transactions (catch mislabeled fraud)
- Confidence scoring (low-confidence predictions flagged for verification)

### 9.4 Bias and Fairness Risks

**Risk 1: Demographic Bias (CRITICAL REGULATORY RISK)**

**Description:** Model discriminates against protected classes
**Example:**
- Higher false positive rate for international customers (country bias)
- Age bias (young customers flagged more often due to new accounts)

**Mitigation:**
- Fairness metrics: Precision parity across demographics
- Sensitive attribute removal: No explicit race, gender, religion features
- Disparate impact testing: FPR similar across countries (<10% difference)
- Regular audits: Quarterly fairness report by compliance team

**Risk 2: Geographic Bias (MEDIUM RISK)**

**Description:** Model over-flags certain countries
**Example:**
- All Nigeria transactions flagged (country stereotyping)
- Legitimate Nigerian customers harmed

**Mitigation:**
- Country risk score (continuous, not binary blacklist)
- Customer-level features (not just country)
- Manual review for high-risk countries (not auto-block)
- Appeal process (customers can challenge decisions)

**Risk 3: Historical Bias Amplification (MEDIUM RISK)**

**Description:** Model learns past human biases
**Example:**
- Historical fraud investigators over-flagged young accounts
- Model amplifies this bias (learns to flag young accounts even more)

**Mitigation:**
- Review historical labels for bias (QA sample)
- Constraint-based learning (enforce fairness constraints)
- Human-in-the-loop (ML suggests, human decides for REVIEW tier)

### 9.5 False Positive Risks

**Risk 1: Customer Churn (HIGH BUSINESS IMPACT)**

**Description:** Legitimate customers frustrated by false blocks
**Example:**
- Customer's card declined at restaurant (embarrassing)
- Customer switches to competitor bank
- Lifetime value loss: $5,000 per churned customer

**Mitigation:**
- High precision threshold (85%+)
- Three-tier system (REVIEW instead of BLOCK for ambiguous)
- Instant appeal process (SMS link to approve transaction)
- Compensation (waive fees for false positive victims)

**Risk 2: Operational Overhead (MEDIUM BUSINESS IMPACT)**

**Description:** False positives burden fraud investigation team
**Example:**
- 1,000 daily false positives × 15 min investigation = 250 hours/day
- Team capacity: 100 hours/day → backlog grows

**Mitigation:**
- Optimize threshold for operational capacity (not just cost)
- Automated rules for obvious legitimate (e.g., repeat merchant)
- Prioritization queue (high-amount FPs reviewed first)

**Risk 3: Revenue Loss (MEDIUM BUSINESS IMPACT)**

**Description:** Legitimate transactions blocked = lost revenue
**Example:**
- Merchant loses $1,000 sale (customer goes elsewhere)
- Platform loses 3% transaction fee = $30
- FP × $30 revenue loss × 1,000 FPs/day = $30K/day = $11M/year

**Mitigation:**
- Measure revenue impact (not just fraud loss)
- Optimize threshold for net revenue (fraud saved - revenue lost)
- Industry benchmarking (is our FP rate competitive?)

### 9.6 False Negative Risks

**Risk 1: Direct Financial Loss (CRITICAL BUSINESS IMPACT)**

**Description:** Fraud not caught = direct loss
**Example:**
- $500 fraudulent transaction approved
- Chargeback + fees = $550 total loss
- 100 FNs/day = $55K/day = $20M/year

**Mitigation:**
- Prioritize recall (75%+ target)
- Cost-sensitive learning (FN 20x more expensive than FP)
- Secondary controls (transaction limits, velocity rules)

**Risk 2: Regulatory Fines (HIGH REGULATORY IMPACT)**

**Description:** Systematic fraud detection failures = regulatory action
**Example:**
- Money laundering not detected (AML violation)
- $10M fine from financial regulator
- Reputational damage

**Mitigation:**
- Regulatory compliance review (legal team approves model)
- Conservative thresholds (prefer false positive over false negative)
- Human oversight (high-value transactions always reviewed)
- Audit trail (prove due diligence)

**Risk 3: Repeat Victimization (MEDIUM BUSINESS IMPACT)**

**Description:** Fraud not caught → customer repeat target
**Example:**
- Stolen card used once (missed), fraudster empties account
- Customer loses trust, switches banks
- Reputational damage

**Mitigation:**
- Rapid response (block card immediately after fraud confirmed)
- Proactive monitoring (flag similar patterns after fraud)
- Customer education (fraud prevention tips)

---

## 10. Deployment Strategy

### 10.1 Deployment Architecture

**Infrastructure:**
- **Model Serving:** TorchServe or TensorFlow Serving (though XGBoost, for standardization)
- **API Gateway:** FastAPI (Python) for REST API
- **Feature Store:** Redis (customer/merchant aggregations)
- **Database:** PostgreSQL (transaction log, labels)
- **Model Registry:** MLflow (model versioning, metadata)
- **Monitoring:** Prometheus (metrics) + Grafana (dashboards)
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana)

**Deployment Flow:**
```
[API Request] → [Load Balancer] → [FastAPI Service]
                                         ↓
                      [Feature Extraction] ← [Redis Cache]
                                         ↓ ← [PostgreSQL]
                      [XGBoost Model] + [Isolation Forest]
                                         ↓
                      [Ensemble & Threshold]
                                         ↓
                      [SHAP Explanation]
                                         ↓
                      [API Response] → [Client]
```

### 10.2 Canary Deployment

**Strategy:** Gradual rollout to minimize risk

**Phases:**

**Phase 1: Shadow Mode (Week 1)**
- New model runs in parallel with production
- Predictions logged but not used
- Compare predictions: old vs new
- Metrics: Prediction correlation, latency, errors
- Success Criteria: Latency <100ms, error rate <0.01%

**Phase 2: Canary 5% (Week 2)**
- 5% of traffic routed to new model
- 95% still on old model
- Monitor for 48 hours
- Metrics: Precision, recall (labeled data), latency, error rate
- Success Criteria: Metrics ±5% of old model, no latency regression

**Phase 3: Canary 25% (Week 3)**
- 25% of traffic to new model
- Monitor for 7 days
- Success Criteria: Metrics ±3% of old model

**Phase 4: Canary 50% (Week 4)**
- 50-50 split test
- A/B comparison (statistical significance)
- Success Criteria: New model ≥ old model (not just non-inferior)

**Phase 5: Full Rollout (Week 5)**
- 100% traffic to new model
- Old model kept as backup (rollback ready)
- Monitor for 2 weeks
- Success Criteria: All KPIs stable or improved

**Rollback Triggers:**
- Error rate >1% (API errors, model crashes)
- Latency p95 >150ms (user experience degraded)
- Precision drops >20% (too many false positives)
- Recall drops >20% (missing too much fraud)
- Any critical alert (data drift, prediction drift)

**Rollback Process:**
- Automatic: Route 100% traffic back to old model (1 minute)
- Manual: On-call engineer confirms rollback (5 minutes)
- Investigation: Root cause analysis (24 hours)
- Fix: Retrain or debug new model (1-7 days)

### 10.3 Blue-Green Deployment

**Alternative to Canary:** Full environment swap

**Setup:**
- Blue: Current production model (v1.0)
- Green: New model (v1.1) in staging environment

**Process:**
1. Deploy v1.1 to Green environment
2. Run integration tests on Green
3. Route 100% test traffic to Green (24 hours)
4. If successful, swap: Green becomes production
5. Blue kept as instant rollback

**Use Case:** Major model changes (architecture swap, feature overhaul)

### 10.4 Model Versioning

**Versioning Scheme:** Semantic versioning (MAJOR.MINOR.PATCH)
- **MAJOR:** Model architecture change (XGBoost → Neural Net)
- **MINOR:** Feature additions, hyperparameter tuning
- **PATCH:** Bug fixes, data updates

**Example:**
- v1.0.0: Initial production model (XGBoost + Isolation Forest)
- v1.1.0: Added 5 new features (device_mismatch, ip_mismatch)
- v1.1.1: Fixed bug in time_since_last_transaction calculation
- v2.0.0: Switched to Neural Network (major change)

**Metadata Stored in MLflow:**
- Model version
- Training date
- Training data date range
- Feature list (47 features)
- Hyperparameters
- Performance metrics (precision, recall, AUC)
- Model artifacts (pickle files, scalers)

### 10.5 A/B Testing Strategy

**Experiment Design:**

**Control:** Current production model (v1.0)
**Treatment:** New model (v1.1)

**Randomization:** Customer-level (not transaction-level)
- Why: Consistency (same customer always sees same model)
- How: Hash(customer_id) % 100 < 50 → Treatment, else Control

**Sample Size:**
- 50-50 split (50K transactions/day per group)
- 7-day test duration = 350K transactions per group
- With 0.5% fraud rate → 1,750 fraud cases per group (sufficient)

**Primary Metric:** Business cost per transaction
**Secondary Metrics:** Precision, recall, F-beta, AUC-PR

**Statistical Test:**
- Two-sample t-test (cost difference)
- Significance level: α=0.05
- Power: 80% (detect 10% cost difference)

**Decision Rule:**
- Treatment significantly better (p<0.05) → deploy new model
- No significant difference → keep current model (simplicity)
- Treatment significantly worse → discard new model

### 10.6 Feature Flags

**Dynamic Configuration:**

**Flag 1: MODEL_VERSION**
- Values: "v1.0", "v1.1", "v1.2"
- Use Case: Instant model swap without redeployment
- Example: "v1.1" causing issues → flip flag to "v1.0"

**Flag 2: ENSEMBLE_WEIGHT**
- Values: 0.0-1.0 (XGBoost weight, IF weight = 1 - value)
- Default: 0.7 (70% XGBoost, 30% Isolation Forest)
- Use Case: Adjust ensemble without retraining

**Flag 3: FRAUD_THRESHOLD**
- Values: 0.0-1.0
- Default: 0.30
- Use Case: Adjust FP/FN tradeoff dynamically

**Flag 4: ENABLE_SHAP_EXPLANATIONS**
- Values: true/false
- Default: true
- Use Case: Disable if SHAP slows inference

**Flag 5: ENABLE_ISOLATION_FOREST**
- Values: true/false
- Default: true
- Use Case: Disable IF if causing issues, use XGBoost only

**Implementation:** LaunchDarkly or custom config service

### 10.7 Disaster Recovery

**Backup Strategy:**

**1. Model Backups**
- Store last 10 model versions in S3
- Retention: 1 year
- Test restore quarterly

**2. Rollback Plan**
- Keep last stable version running in standby
- One-click rollback via feature flag
- Rollback time: <5 minutes

**3. Fallback to Rules**
- If all ML models fail → rule-based system activates
- Simple heuristics (amount >$5K → review, historical_fraud_count >0 → review)
- Lower performance but prevents total failure

**4. Database Backups**
- PostgreSQL: Daily full backup, hourly incremental
- Redis: RDB snapshots every 6 hours
- Recovery time objective (RTO): 1 hour
- Recovery point objective (RPO): 1 hour (max data loss)

---

## 11. Deliverables

### 11.1 ML Architecture Document

**Document:** `ML_ARCHITECTURE.md`

**Contents:**
1. System overview diagram (data flow, components)
2. Component responsibilities (API, feature store, model serving)
3. Technology stack (FastAPI, XGBoost, Redis, PostgreSQL)
4. Scalability plan (horizontal scaling, load balancing)
5. Security considerations (API auth, model encryption)

**Audience:** Engineering team, DevOps, architects

### 11.2 Feature Dictionary

**Document:** `FEATURE_DICTIONARY.md`

**Contents:**
- All 47 features listed
- Each feature: Name, definition, type, range, source, importance
- Business justification for each feature
- SQL queries or formulas for aggregation features
- Data lineage (upstream tables, transformations)

**Audience:** ML engineers, data scientists, product managers

### 11.3 Training Pipeline Documentation

**Document:** `TRAINING_PIPELINE.md`

**Contents:**
1. Data extraction (SQL queries, date ranges)
2. Preprocessing steps (cleaning, imputation, outliers)
3. Feature engineering (aggregations, interactions)
4. Encoding and scaling (one-hot, target encoding, standardization)
5. Train/val/test split (temporal, stratified)
6. SMOTE application (ratio, k-neighbors)
7. Model training (XGBoost hyperparameters, early stopping)
8. Evaluation metrics (precision, recall, AUC-PR, cost)
9. Model serialization (save format, artifacts)

**Audience:** ML engineers, data scientists

### 11.4 Inference Pipeline Documentation

**Document:** `INFERENCE_PIPELINE.md`

**Contents:**
1. API endpoint specification (request/response schemas)
2. Feature extraction (database queries, Redis lookups)
3. Preprocessing (same as training, with saved transformers)
4. Model loading (deserialization, memory management)
5. Ensemble scoring (XGBoost + Isolation Forest weights)
6. Threshold application (BLOCK, REVIEW, APPROVE rules)
7. SHAP explanation generation (top 10 features)
8. Response formatting (JSON structure)
9. Error handling (timeout, missing data, model unavailable)
10. Latency optimization (caching, batch inference)

**Audience:** ML engineers, backend engineers, DevOps

### 11.5 Evaluation Strategy Document

**Document:** `EVALUATION_STRATEGY.md`

**Contents:**
1. Metrics definitions (precision, recall, F-beta, AUC-PR, cost)
2. Threshold selection methodology (cost-based optimization)
3. Test set protocol (temporal split, no peeking)
4. Success criteria (metric targets)
5. Error analysis process (FP/FN investigation)
6. Segment analysis (by amount, customer age, geography)
7. Comparison to baselines (logistic regression, rule-based)

**Audience:** ML engineers, product managers, stakeholders

### 11.6 Monitoring Strategy Document

**Document:** `MONITORING_STRATEGY.md`

**Contents:**
1. Data drift monitoring (PSI, feature distributions)
2. Concept drift monitoring (performance degradation)
3. Prediction drift monitoring (score distribution)
4. Feature drift monitoring (missing rates, OOR values)
5. Latency monitoring (p50, p95, p99 SLAs)
6. Model quality metrics (precision, recall, AUC-PR)
7. Alerting rules (critical, high, medium priority)
8. Dashboard specifications (Grafana panels)
9. On-call runbooks (incident response procedures)

**Audience:** ML engineers, DevOps, on-call engineers

### 11.7 Deployment Strategy Document

**Document:** `DEPLOYMENT_STRATEGY.md`

**Contents:**
1. Infrastructure architecture (servers, load balancers, databases)
2. Canary deployment phases (shadow, 5%, 25%, 50%, 100%)
3. Rollback procedures (triggers, process, recovery time)
4. Blue-green deployment (alternative strategy)
5. Model versioning (semantic versioning, MLflow registry)
6. A/B testing protocol (experiment design, statistical tests)
7. Feature flags (dynamic configuration, instant rollback)
8. Disaster recovery (backups, failover, RTO/RPO)

**Audience:** DevOps, ML engineers, platform engineers

### 11.8 Explainability Documentation

**Document:** `EXPLAINABILITY_DOCUMENTATION.md`

**Contents:**
1. SHAP methodology (Shapley values, TreeSHAP algorithm)
2. Global explainability (feature importance, summary plots)
3. Local explainability (waterfall plots, per-prediction explanations)
4. Business translation table (SHAP values → plain English)
5. Regulatory compliance (GDPR Article 22 requirements)
6. Customer-facing explanations (non-technical language)
7. Investigator dashboard (SHAP visualization tools)
8. Performance impact (latency overhead of explanation generation)

**Audience:** ML engineers, fraud investigators, product managers, legal/compliance

### 11.9 Risk Management Plan

**Document:** `RISK_MANAGEMENT_PLAN.md`

**Contents:**
1. Data leakage risks (temporal, target, training-serving skew)
2. Concept drift risks (adversarial adaptation, seasonal drift)
3. Label delay risks (incomplete labels, quality degradation)
4. Bias and fairness risks (demographic, geographic, historical)
5. False positive risks (customer churn, operational overhead)
6. False negative risks (financial loss, regulatory fines)
7. Mitigation strategies for each risk
8. Risk monitoring (metrics, thresholds, alerts)
9. Incident response procedures (escalation, root cause analysis)

**Audience:** ML engineers, risk management, compliance, executives

### 11.10 Model Performance Baseline Report

**Document:** `BASELINE_PERFORMANCE_REPORT.md`

**Contents:**
1. Test set results (precision, recall, F1, F-beta, AUC-ROC, AUC-PR)
2. Confusion matrix (TP, FP, FN, TN counts)
3. Business cost analysis (FN cost + FP cost, net savings)
4. Comparison to baselines (logistic regression, rule-based system)
5. Error analysis (FP/FN case studies)
6. Segment performance (by amount bracket, customer age, geography)
7. Feature importance ranking (SHAP global importance)
8. Calibration curve (predicted vs actual fraud rate)
9. Performance over time (weekly metrics on test set)
10. Executive summary (key findings, recommendations)

**Audience:** Stakeholders, product managers, executives, ML team

### 11.11 Operational Runbooks

**Documents:**

**11.11.1 `RUNBOOK_MODEL_RETRAINING.md`**
- When to retrain (scheduled, performance-triggered, drift-triggered)
- Retraining process (data extraction, training, validation, deployment)
- Approval workflow (who approves, escalation path)
- Rollback if new model worse

**11.11.2 `RUNBOOK_INCIDENT_RESPONSE.md`**
- Model unavailable (503 errors) → restart service, check dependencies
- High latency (p95 >200ms) → check Redis, database, scaling
- Prediction drift → rollback model, investigate data pipeline
- Data drift → analyze feature distributions, consider retraining
- Zero predictions → check model file, feature availability

**11.11.3 `RUNBOOK_MODEL_ROLLBACK.md`**
- Rollback triggers (error rate, latency, performance drops)
- Rollback process (feature flag flip, traffic rerouting)
- Rollback verification (metrics check, smoke tests)
- Post-rollback analysis (root cause, fix timeline)

**Audience:** On-call engineers, ML engineers, DevOps

### 11.12 Testing Strategy Document

**Document:** `TESTING_STRATEGY.md`

**Contents:**

**1. Unit Tests**
- Feature extraction functions (correct calculations)
- Preprocessing functions (encoding, scaling, imputation)
- Model inference (input → output shape, type checks)
- Threshold application (decision logic)

**2. Integration Tests**
- End-to-end pipeline (raw data → prediction)
- Database connectivity (query execution, connection pooling)
- Redis caching (hit rate, staleness)
- API endpoints (request → response)

**3. Data Validation Tests**
- Schema validation (column types, required fields)
- Range validation (amounts >0, scores in [0,1])
- Referential integrity (customer_id exists, merchant_id valid)
- Missing value checks (<5% missing for critical features)

**4. Model Validation Tests**
- Prediction range (probabilities in [0,1])
- Ensemble weights sum to 1.0
- Calibration check (predicted vs actual fraud rate)
- Feature importance sum (SHAP values sum to prediction - baseline)

**5. Performance Tests**
- Latency benchmark (p50, p95, p99 under load)
- Throughput test (max PPS before degradation)
- Memory usage (model size, feature cache size)
- Concurrency test (100 concurrent requests)

**6. Regression Tests**
- Fixed test cases (known fraud/legitimate examples)
- Predictions must not change unless model version changes
- Feature values must match expected (no preprocessing bugs)

**Audience:** ML engineers, QA engineers, DevOps

---

## 12. Executive Summary Table

| **Aspect** | **Decision** | **Rationale** |
|------------|--------------|---------------|
| **Primary Model** | XGBoost (Gradient Boosting) | Best performance on tabular data, handles imbalance, fast inference (<10ms) |
| **Secondary Model** | Isolation Forest (Unsupervised) | Detects novel fraud patterns, complements XGBoost |
| **Why NOT Deep Learning** | Insufficient labeled data (25K fraud cases), no proven advantage, higher latency |
| **Training Data** | 50M transactions, 2 years, 0.5% fraud rate | Sufficient for XGBoost, captures seasonal patterns |
| **Features** | 47 total (35 raw + 12 engineered) | Mix of transaction, customer, merchant, temporal, interaction |
| **Most Important Features** | historical_fraud_count, impossible_travel, amount_ratio, merchant_fraud_rate | Domain-driven + data-driven selection |
| **Class Imbalance** | SMOTE (1:200 → 1:20) + Class Weights (20x FN penalty) | Partial rebalancing + cost-sensitive learning |
| **Evaluation Metric** | AUC-PR (primary), Business Cost (ultimate) | AUC-PR better for imbalance, cost aligns with business |
| **Target Performance** | Precision ≥85%, Recall ≥75%, AUC-PR ≥0.70, Cost <$0.20/txn | Balances FP/FN costs |
| **Threshold** | 0.30 (optimized for business cost, not 0.5) | Lower threshold prioritizes recall (FN 20x more expensive) |
| **Decision Tiers** | BLOCK (≥0.85), REVIEW (0.30-0.85), APPROVE (<0.30) | Three-tier system balances automation and human review |
| **Explainability** | SHAP (global + local explanations) | Regulatory compliance (GDPR), customer trust, debugging |
| **Monitoring** | Data drift (PSI), Concept drift (performance), Prediction drift (KL-div) | Proactive detection of model degradation |
| **Retraining** | Monthly (scheduled), Ad-hoc (performance drops >15%) | Adapt to new fraud patterns, maintain accuracy |
| **Deployment** | Canary (5% → 25% → 50% → 100% over 4 weeks) | Gradual rollout minimizes risk |
| **Latency SLA** | p50 <50ms, p95 <100ms, p99 <200ms | Real-time inference, good user experience |
| **Infrastructure** | FastAPI + Redis + PostgreSQL + XGBoost (CPU) | Fast, scalable, cost-effective |
| **Risk Management** | Data leakage prevention, fairness audits, rollback plan | Mitigate ML risks, regulatory compliance |
| **Business Impact** | $10M annual savings (net fraud prevented - FP costs) | ROI positive, justifies ML investment |

---

## 13. Approval Sign-Offs

This design specification requires approval from the following stakeholders before implementation:

| **Role** | **Name** | **Signature** | **Date** |
|----------|----------|---------------|----------|
| **ML Engineering Lead** | _________________ | _________________ | _______ |
| **Product Owner** | _________________ | _________________ | _______ |
| **Engineering Manager** | _________________ | _________________ | _______ |
| **Risk Management** | _________________ | _________________ | _______ |
| **Compliance Officer** | _________________ | _________________ | _______ |
| **Data Engineering Lead** | _________________ | _________________ | _______ |
| **Chief Technology Officer** | _________________ | _________________ | _______ |

**Approval Criteria:**
- All technical decisions reviewed and validated
- Business metrics align with company objectives
- Risk management plan comprehensive and acceptable
- Regulatory compliance requirements met
- Resource allocation (compute, personnel) approved
- Timeline and milestones feasible

**Post-Approval Actions:**
1. Create implementation tickets in project management system
2. Allocate engineering resources (ML engineers, data engineers, DevOps)
3. Provision infrastructure (AWS EC2, RDS, ElastiCache)
4. Begin implementation Phase 1: Data pipeline and feature engineering
5. Schedule weekly sync meetings with stakeholders
6. Set up monitoring dashboards and alerting

---

## 14. Appendices

### Appendix A: Glossary

**AUC-PR:** Area Under Precision-Recall Curve - measures model ranking quality for imbalanced data  
**AUC-ROC:** Area Under Receiver Operating Characteristic Curve - measures model discrimination ability  
**Calibration:** Alignment between predicted probabilities and actual fraud rates  
**Concept Drift:** Change in relationship between features and target over time  
**Cost-Sensitive Learning:** Training models with asymmetric error costs (FN ≠ FP)  
**Data Drift:** Change in input feature distributions over time  
**F-beta Score:** Weighted harmonic mean of precision and recall (β controls weight)  
**False Negative (FN):** Fraud case missed by model (Type II error)  
**False Positive (FP):** Legitimate transaction flagged as fraud (Type I error)  
**Isolation Forest:** Unsupervised anomaly detection algorithm based on decision trees  
**Label Delay:** Time between transaction occurrence and fraud label assignment  
**Precision:** % of predicted fraud that is actually fraud (TP / (TP + FP))  
**Recall:** % of actual fraud caught by model (TP / (TP + FN))  
**SHAP:** SHapley Additive exPlanations - method to explain model predictions  
**SMOTE:** Synthetic Minority Over-sampling Technique - generates synthetic fraud examples  
**Target Encoding:** Replacing categorical values with mean target rate  
**Temporal Leakage:** Using future information to predict past events (data bug)  
**True Negative (TN):** Legitimate transaction correctly approved  
**True Positive (TP):** Fraud case correctly detected  
**XGBoost:** Extreme Gradient Boosting - ensemble of decision trees trained sequentially  

### Appendix B: Feature Engineering Formulas

**Haversine Distance (km):**
```
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
c = 2 × atan2(√a, √(1−a))
distance = R × c  (R = 6371 km, Earth radius)
```

**Population Stability Index (PSI):**
```
PSI = Σ (actual% - expected%) × ln(actual% / expected%)
```

**Target Encoding (Smoothed Mean):**
```
encoded_value = (count × mean_category + α × global_mean) / (count + α)
where α = smoothing parameter (default 10)
```

**Impossible Travel Detection:**
```
speed = distance_km / time_hours
impossible_travel = 1 if speed > 800 km/h (airplane speed), else 0
```

**Cyclical Encoding:**
```
hour_sin = sin(2π × hour / 24)
hour_cos = cos(2π × hour / 24)
```

### Appendix C: XGBoost Hyperparameter Guide

| **Parameter** | **Value** | **Purpose** | **Tuning Range** |
|---------------|-----------|-------------|------------------|
| `max_depth` | 8 | Tree depth (prevents overfitting) | [3, 15] |
| `learning_rate` | 0.05 | Step size (slower = better generalization) | [0.01, 0.3] |
| `n_estimators` | 500 | Number of trees (with early stopping) | [100, 1000] |
| `min_child_weight` | 50 | Minimum samples per leaf | [10, 100] |
| `subsample` | 0.8 | Row sampling ratio | [0.5, 1.0] |
| `colsample_bytree` | 0.8 | Column sampling ratio | [0.5, 1.0] |
| `scale_pos_weight` | 20 | FN penalty (FN cost / FP cost) | [10, 50] |
| `gamma` | 0.1 | Minimum loss reduction for split | [0, 1.0] |
| `reg_alpha` | 0.1 | L1 regularization | [0, 1.0] |
| `reg_lambda` | 1.0 | L2 regularization | [0, 10] |

**Tuning Strategy:**
1. Fix `n_estimators=1000`, tune `max_depth` and `min_child_weight` (tree structure)
2. Tune `subsample` and `colsample_bytree` (randomness)
3. Tune `learning_rate` (reduce, increase `n_estimators` proportionally)
4. Tune `gamma`, `reg_alpha`, `reg_lambda` (regularization)
5. Tune `scale_pos_weight` (class balance)

### Appendix D: Metric Calculation Examples

**Example Transaction Set:**
- Total transactions: 100,000
- Actual fraud: 500 (0.5%)
- Actual legitimate: 99,500 (99.5%)
- Model predictions:
  - True Positives (TP): 400 (fraud correctly detected)
  - False Negatives (FN): 100 (fraud missed)
  - False Positives (FP): 50 (legitimate flagged)
  - True Negatives (TN): 99,450 (legitimate approved)

**Calculations:**
```
Precision = TP / (TP + FP) = 400 / (400 + 50) = 88.9%
Recall = TP / (TP + FN) = 400 / (400 + 100) = 80.0%
F1 = 2 × (Precision × Recall) / (Precision + Recall) = 84.2%
F2 = 5 × (Precision × Recall) / (4 × Precision + Recall) = 81.6%

Business Cost:
FN Cost = 100 × $500 = $50,000
FP Cost = 50 × $25 = $1,250
Total Cost = $51,250
Cost per Transaction = $51,250 / 100,000 = $0.51

Net Savings:
Without model: 500 × $500 = $250,000 loss
With model: $51,250 loss
Savings = $250,000 - $51,250 = $198,750 (79% reduction)
```

### Appendix E: Regulatory References

**GDPR (General Data Protection Regulation):**
- **Article 6(1)(f):** Legitimate interest for fraud prevention
- **Article 13:** Right to information about automated decision-making
- **Article 22:** Right to explanation and human review for automated decisions
- **Recital 71:** Profiling requirements and safeguards

**PCI-DSS (Payment Card Industry Data Security Standard):**
- **Requirement 8:** Identify and authenticate access to system components
- **Requirement 10:** Track and monitor all access to network resources and cardholder data
- **Requirement 11:** Regularly test security systems and processes

**CCPA (California Consumer Privacy Act):**
- **Section 1798.100:** Right to know what personal information is collected
- **Section 1798.105:** Right to deletion of personal information
- **Section 1798.120:** Right to opt-out of sale of personal information

**SOC 2 (Service Organization Control 2):**
- **Security:** Protection against unauthorized access
- **Availability:** System operational and usable as committed
- **Confidentiality:** Information designated as confidential is protected

### Appendix F: References and Resources

**Academic Papers:**
1. Chen, T., & Guestrin, C. (2016). "XGBoost: A Scalable Tree Boosting System." KDD '16.
2. Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). "Isolation Forest." ICDM '08.
3. Lundberg, S. M., & Lee, S. I. (2017). "A Unified Approach to Interpreting Model Predictions." NIPS '17.
4. Chawla, N. V., et al. (2002). "SMOTE: Synthetic Minority Over-sampling Technique." JAIR.

**Industry Best Practices:**
1. Stripe: "Machine Learning for Fraud Detection" (Blog, 2020)
2. PayPal: "Risk Management and Fraud Prevention" (White Paper, 2019)
3. AWS: "Fraud Detection using Machine Learning" (Solution Architecture, 2021)
4. Google Cloud: "Best Practices for ML Model Deployment" (Documentation, 2022)

**Books:**
1. Géron, A. (2019). "Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow." O'Reilly.
2. Provost, F., & Fawcett, T. (2013). "Data Science for Business." O'Reilly.
3. Kuhn, M., & Johnson, K. (2019). "Feature Engineering and Selection." CRC Press.

**Tools and Libraries:**
1. XGBoost: https://xgboost.readthedocs.io/
2. Scikit-learn: https://scikit-learn.org/
3. SHAP: https://shap.readthedocs.io/
4. MLflow: https://mlflow.org/
5. Imbalanced-learn: https://imbalanced-learn.org/

---

## Document Change Log

| **Version** | **Date** | **Author** | **Changes** |
|-------------|----------|------------|-------------|
| 0.1 | 2026-07-01 | ML Team | Initial draft |
| 0.5 | 2026-07-03 | ML Team | Added feature engineering details |
| 0.8 | 2026-07-05 | ML Team | Added model selection rationale |
| 0.9 | 2026-07-06 | ML Team | Added monitoring and deployment strategies |
| 1.0 | 2026-07-07 | ML Team | Final review, added appendices, ready for approval |

---

## Next Steps

### Immediate Actions (Week 1-2)

1. **Stakeholder Review:** Circulate document to all stakeholders for feedback
2. **Approval Meeting:** Schedule design review meeting with all approvers
3. **Infrastructure Setup:** Provision AWS resources (EC2, RDS, ElastiCache, S3)
4. **Data Access:** Confirm database access, data export permissions
5. **Team Allocation:** Assign ML engineers, data engineers, DevOps to project

### Implementation Phase 1: Data Pipeline (Week 3-6)

1. Extract historical transaction data (50M transactions, 2 years)
2. Implement preprocessing pipeline (cleaning, validation, imputation)
3. Implement feature engineering (47 features, aggregations, interactions)
4. Set up feature store (Redis caching layer)
5. Create train/val/test splits (temporal, stratified)
6. Data quality validation (schema checks, range checks, missing value analysis)

### Implementation Phase 2: Model Training (Week 7-10)

1. Implement SMOTE for class balancing
2. Train XGBoost with Bayesian hyperparameter tuning
3. Train Isolation Forest (unsupervised)
4. Implement ensemble (weighted average, tuning)
5. Threshold optimization (cost-based selection)
6. Model serialization and versioning (MLflow)

### Implementation Phase 3: Evaluation (Week 11-12)

1. Generate predictions on test set
2. Calculate all metrics (precision, recall, F-beta, AUC-PR, cost)
3. Error analysis (FP/FN case studies)
4. Segment analysis (by amount, customer age, geography)
5. SHAP global/local explanations
6. Baseline comparison (vs logistic regression, rules)
7. Performance report and stakeholder presentation

### Implementation Phase 4: Deployment (Week 13-16)

1. Build FastAPI inference service
2. Integration with feature store (Redis)
3. Load testing (latency, throughput)
4. Shadow deployment (parallel with production rules)
5. Canary deployment (5% → 25% → 50% → 100%)
6. Monitoring dashboards (Grafana)
7. Alerting setup (Prometheus)
8. Runbook documentation

### Post-Deployment (Week 17+)

1. Daily monitoring (data drift, performance, latency)
2. Weekly metric reviews (precision, recall, cost)
3. Monthly model retraining (scheduled)
4. Quarterly fairness audits (bias detection)
5. Continuous improvement (new features, hyperparameter tuning)
6. Incident response (rollback if needed)

---

**END OF ML DESIGN SPECIFICATION**

---

**Document Status:** ✅ COMPLETE - Ready for Stakeholder Review and Approval

**Total Pages:** 85  
**Total Sections:** 14  
**Total Features Defined:** 47  
**Total Appendices:** 6  

**Key Highlights:**
- Comprehensive ML design covering all aspects from data to deployment
- No code implementation (design-only as requested)
- Includes business justification for every decision
- Risk management and mitigation strategies documented
- Regulatory compliance (GDPR, PCI-DSS) addressed
- Production-ready deployment strategy with monitoring
- Clear success metrics and approval process

**This document serves as the single source of truth for ML implementation. All code implementation must align with this specification.**
