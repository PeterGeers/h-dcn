"""
Centraal configuratiebestand voor Python scripts.
Waarden komen overeen met scripts/config.sh.
"""
import os

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://petergeers.github.io/h-dcn")
API_BASE_URL = os.environ.get("API_BASE_URL", "https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev")
AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "eu-west-1_OAT3oPCIm")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "6unl8mg5tbv5r727vc39d847vn")
DYNAMODB_MEMBERS_TABLE = os.environ.get("DYNAMODB_MEMBERS_TABLE", "Members")
