from fastapi.testclient import TestClient
from src.presentation.main import create_application

app = create_application()
client = TestClient(app)
for path in ["/v1/docs", "/v1/redoc", "/v1/openapi.json"]:
    response = client.get(path)
    print(path, response.status_code)
