$env:AWS_SAM_STACK_NAME="webshop-backend"
python -m pytest tests/integration/test_api_gateway.py::TestApiGateway::test_all_apis -v -s