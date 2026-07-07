"""Infrastructure Layer - External adapters and implementations.

This layer contains:
- Database implementations (SQLAlchemy)
- ML service implementations (Future: XGBoost, SHAP)
- Storage implementations (S3)
- Monitoring implementations (CloudWatch)
- Security implementations (JWT, Secrets Manager)

This layer depends on application and domain layers but NOT vice versa.
"""
