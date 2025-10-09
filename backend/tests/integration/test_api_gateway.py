import os
import json
import uuid
from datetime import datetime
from unittest import TestCase

import boto3
import requests

"""
Comprehensive API Gateway tests for all 7 DynamoDB tables in HDCN Backend.
Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test.
"""


class TestApiGateway(TestCase):
    api_endpoint: str
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_results = []
        self.created_resources = {}

    @classmethod
    def get_and_verify_stack_name(cls) -> str:
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        if not stack_name:
            raise Exception(
                "Cannot find env var AWS_SAM_STACK_NAME. \n"
                "Please setup this environment variable with the stack name where we are running integration tests."
            )

        # Verify stack exists
        client = boto3.client("cloudformation")
        try:
            client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name}. \n" f'Please make sure stack with the name "{stack_name}" exists.'
            ) from e

        return stack_name

    def setUp(self) -> None:
        """
        Get API Gateway endpoint from CloudFormation stack outputs
        """
        stack_name = TestApiGateway.get_and_verify_stack_name()
        client = boto3.client("cloudformation")
        response = client.describe_stacks(StackName=stack_name)
        stacks = response["Stacks"]
        self.assertTrue(stacks, f"Cannot find stack {stack_name}")

        stack_outputs = stacks[0]["Outputs"]
        api_outputs = [output for output in stack_outputs if output["OutputKey"] == "ApiBaseUrl"]
        self.assertTrue(api_outputs, f"Cannot find output ApiBaseUrl in stack {stack_name}")
        self.api_endpoint = api_outputs[0]["OutputValue"]

    def log_test_result(self, table, method, endpoint, status_code, success, details="", key_used=""):
        """Log test results for HTML report generation"""
        self.test_results.append({
            'table': table,
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'success': success,
            'details': details,
            'key_used': key_used,
            'timestamp': datetime.now().isoformat()
        })

    def test_products_api(self):
        """Test all Product API endpoints"""
        # CREATE Product
        product_data = {
            "name": "Test Harley T-Shirt",
            "price": "29.99",
            "description": "Official HDCN merchandise",
            "category": "clothing"
        }
        response = requests.post(f"{self.api_endpoint}/insert-product/", json=product_data)
        success = response.status_code == 201
        product_id = response.json().get('id') if success else None
        if product_id:
            self.created_resources['product_id'] = product_id
        self.log_test_result('Products', 'POST', '/insert-product/', response.status_code, success, 
                           response.text, f"id: {product_id}")

        # GET All Products
        response = requests.get(f"{self.api_endpoint}/scan-product/")
        success = response.status_code == 200
        self.log_test_result('Products', 'GET', '/scan-product/', response.status_code, success, 
                           f"Retrieved {len(response.json()) if success else 0} products")

        # Test individual product operations if we have an ID
        if product_id:
            # GET Product by ID
            response = requests.get(f"{self.api_endpoint}/getproduct-byid/{product_id}")
            success = response.status_code == 200
            self.log_test_result('Products', 'GET', f'/getproduct-byid/{product_id}', response.status_code, success, 
                               response.text, f"id: {product_id}")

            # UPDATE Product
            update_data = {"name": "Updated Harley T-Shirt", "price": "34.99"}
            response = requests.put(f"{self.api_endpoint}/update-product/{product_id}", json=update_data)
            success = response.status_code == 200
            self.log_test_result('Products', 'PUT', f'/update-product/{product_id}', response.status_code, success, 
                               response.text, f"id: {product_id}")

            # DELETE Product
            response = requests.delete(f"{self.api_endpoint}/delete-product/{product_id}")
            success = response.status_code == 200
            self.log_test_result('Products', 'DELETE', f'/delete-product/{product_id}', response.status_code, success, 
                               response.text, f"id: {product_id}")
        else:
            self.log_test_result('Products', 'GET', '/getproduct-byid/{id}', 0, False, 
                               "Skipped - no product ID available", "Requires product ID")
            self.log_test_result('Products', 'PUT', '/update-product/{id}', 0, False, 
                               "Skipped - no product ID available", "Requires product ID")
            self.log_test_result('Products', 'DELETE', '/delete-product/{id}', 0, False, 
                               "Skipped - no product ID available", "Requires product ID")

    def test_members_api(self):
        """Test all Member API endpoints"""
        # CREATE Member
        member_data = {
            "name": "Jan de Vries",
            "email": "jan@hdcn-test.nl",
            "phone": "0612345678",
            "city": "Amsterdam"
        }
        response = requests.post(f"{self.api_endpoint}/members", json=member_data)
        success = response.status_code == 201
        member_id = response.json().get('member_id') if success else None  # Changed from 'id' to 'member_id'
        if member_id:
            self.created_resources['member_id'] = member_id
        self.log_test_result('Members', 'POST', '/members', response.status_code, success, 
                           response.text, f"member_id: {member_id}")

        # GET All Members
        response = requests.get(f"{self.api_endpoint}/members")
        success = response.status_code == 200
        self.log_test_result('Members', 'GET', '/members', response.status_code, success, 
                           f"Retrieved {len(response.json()) if success else 0} members")

        if member_id:
            # GET Member by ID
            response = requests.get(f"{self.api_endpoint}/members/{member_id}")
            success = response.status_code == 200
            self.log_test_result('Members', 'GET', f'/members/{member_id}', response.status_code, success, 
                               response.text, f"member_id: {member_id}")

            # UPDATE Member
            update_data = {"name": "Jan de Vries Jr.", "city": "Rotterdam"}
            response = requests.put(f"{self.api_endpoint}/members/{member_id}", json=update_data)
            success = response.status_code == 200
            self.log_test_result('Members', 'PUT', f'/members/{member_id}', response.status_code, success, 
                               response.text, f"member_id: {member_id}")

            # DELETE Member
            response = requests.delete(f"{self.api_endpoint}/members/{member_id}")
            success = response.status_code == 200
            self.log_test_result('Members', 'DELETE', f'/members/{member_id}', response.status_code, success, 
                               response.text, f"member_id: {member_id}")
        else:
            self.log_test_result('Members', 'GET', '/members/{id}', 0, False, 
                               "Skipped - no member ID available", "Requires member ID")
            self.log_test_result('Members', 'PUT', '/members/{id}', 0, False, 
                               "Skipped - no member ID available", "Requires member ID")
            self.log_test_result('Members', 'DELETE', '/members/{id}', 0, False, 
                               "Skipped - no member ID available", "Requires member ID")

    def test_payments_api(self):
        """Test all Payment API endpoints"""
        member_id = self.created_resources.get('member_id', 'test_member_123')
        
        # CREATE Payment
        payment_data = {
            "member_id": member_id,
            "amount": "75.00",
            "payment_type": "membership",
            "description": "Annual membership fee 2024"
        }
        response = requests.post(f"{self.api_endpoint}/payments", json=payment_data)
        success = response.status_code == 201
        payment_id = response.json().get('payment_id') if success else None
        if payment_id:
            self.created_resources['payment_id'] = payment_id
        self.log_test_result('Payments', 'POST', '/payments', response.status_code, success, 
                           response.text, f"payment_id: {payment_id}")

        # GET All Payments
        response = requests.get(f"{self.api_endpoint}/payments")
        success = response.status_code == 200
        self.log_test_result('Payments', 'GET', '/payments', response.status_code, success, 
                           f"Retrieved {len(response.json()) if success else 0} payments")

        if payment_id:
            # GET Payment by ID
            response = requests.get(f"{self.api_endpoint}/payments/{payment_id}")
            success = response.status_code == 200
            self.log_test_result('Payments', 'GET', f'/payments/{payment_id}', response.status_code, success, 
                               response.text, f"payment_id: {payment_id}")

            # UPDATE Payment
            update_data = {"amount": "85.00", "description": "Updated membership fee"}
            response = requests.put(f"{self.api_endpoint}/payments/{payment_id}", json=update_data)
            success = response.status_code == 200
            self.log_test_result('Payments', 'PUT', f'/payments/{payment_id}', response.status_code, success, 
                               response.text, f"payment_id: {payment_id}")

            # DELETE Payment
            response = requests.delete(f"{self.api_endpoint}/payments/{payment_id}")
            success = response.status_code == 200
            self.log_test_result('Payments', 'DELETE', f'/payments/{payment_id}', response.status_code, success, 
                               response.text, f"payment_id: {payment_id}")

        # GET Member Payments
        response = requests.get(f"{self.api_endpoint}/payments/member/{member_id}")
        success = response.status_code == 200
        self.log_test_result('Payments', 'GET', f'/payments/member/{member_id}', response.status_code, success, 
                           response.text, f"member_id: {member_id}")

    def test_events_api(self):
        """Test all Event API endpoints"""
        # CREATE Event
        event_data = {
            "naam": "Voorjaarsrit 2024",
            "datum_van": "2024-04-15",
            "datum_tot": "2024-04-15",
            "locatie": "Café De Biker, Volendam",
            "beschrijving": "Jaarlijkse voorjaarsrit door Noord-Holland"
        }
        response = requests.post(f"{self.api_endpoint}/events", json=event_data)
        success = response.status_code == 201
        event_id = response.json().get('event_id') if success else None
        if event_id:
            self.created_resources['event_id'] = event_id
        self.log_test_result('Events', 'POST', '/events', response.status_code, success, 
                           response.text, f"event_id: {event_id}")

        # GET All Events
        response = requests.get(f"{self.api_endpoint}/events")
        success = response.status_code == 200
        self.log_test_result('Events', 'GET', '/events', response.status_code, success, 
                           f"Retrieved {len(response.json()) if success else 0} events")

        if event_id:
            # GET Event by ID
            response = requests.get(f"{self.api_endpoint}/events/{event_id}")
            success = response.status_code == 200
            self.log_test_result('Events', 'GET', f'/events/{event_id}', response.status_code, success, 
                               response.text, f"event_id: {event_id}")

            # UPDATE Event
            update_data = {"naam": "Voorjaarsrit 2024 - Updated", "aantal_deelnemers": "25"}
            response = requests.put(f"{self.api_endpoint}/events/{event_id}", json=update_data)
            success = response.status_code == 200
            self.log_test_result('Events', 'PUT', f'/events/{event_id}', response.status_code, success, 
                               response.text, f"event_id: {event_id}")

            # DELETE Event
            response = requests.delete(f"{self.api_endpoint}/events/{event_id}")
            success = response.status_code in [200, 204]  # Accept both 200 and 204 for DELETE
            self.log_test_result('Events', 'DELETE', f'/events/{event_id}', response.status_code, success, 
                               response.text, f"event_id: {event_id}")

    def test_memberships_api(self):
        """Test all Membership API endpoints"""
        # CREATE Membership
        membership_data = {
            "name": "Premium Membership",
            "price": "99.99",
            "duration_months": "12",
            "description": "Full access premium membership"
        }
        response = requests.post(f"{self.api_endpoint}/memberships", json=membership_data)
        success = response.status_code == 201
        membership_id = response.json().get('membership_type_id') if success else None
        if membership_id:
            self.created_resources['membership_id'] = membership_id
        self.log_test_result('Memberships', 'POST', '/memberships', response.status_code, success, 
                           response.text, f"membership_type_id: {membership_id}")

        # GET All Memberships
        response = requests.get(f"{self.api_endpoint}/memberships")
        success = response.status_code == 200
        self.log_test_result('Memberships', 'GET', '/memberships', response.status_code, success, 
                           f"Retrieved {len(response.json()) if success else 0} memberships")

        if membership_id:
            # GET Membership by ID
            response = requests.get(f"{self.api_endpoint}/memberships/{membership_id}")
            success = response.status_code == 200
            self.log_test_result('Memberships', 'GET', f'/memberships/{membership_id}', response.status_code, success, 
                               response.text, f"membership_type_id: {membership_id}")

            # UPDATE Membership
            update_data = {"name": "Premium Plus Membership", "price": "149.99"}
            response = requests.put(f"{self.api_endpoint}/memberships/{membership_id}", json=update_data)
            success = response.status_code == 200
            self.log_test_result('Memberships', 'PUT', f'/memberships/{membership_id}', response.status_code, success, 
                               response.text, f"membership_type_id: {membership_id}")

            # DELETE Membership
            response = requests.delete(f"{self.api_endpoint}/memberships/{membership_id}")
            success = response.status_code == 200
            self.log_test_result('Memberships', 'DELETE', f'/memberships/{membership_id}', response.status_code, success, 
                               response.text, f"membership_type_id: {membership_id}")

    def test_carts_api(self):
        """Test all Cart API endpoints"""
        # CREATE Cart
        cart_data = {
            "customer_id": "test_customer_123",
            "items": [],
            "total_amount": "0.00"
        }
        response = requests.post(f"{self.api_endpoint}/carts", json=cart_data)
        success = response.status_code == 201
        cart_id = response.json().get('cart_id') if success else None
        if cart_id:
            self.created_resources['cart_id'] = cart_id
        self.log_test_result('Carts', 'POST', '/carts', response.status_code, success, 
                           response.text, f"cart_id: {cart_id}")

        if cart_id:
            # GET Cart by ID
            response = requests.get(f"{self.api_endpoint}/carts/{cart_id}")
            success = response.status_code == 200
            self.log_test_result('Carts', 'GET', f'/carts/{cart_id}', response.status_code, success, 
                               response.text, f"cart_id: {cart_id}")

            # UPDATE Cart Items
            update_data = {
                "items": [{"product_id": "prod_001", "quantity": "2"}],
                "total_amount": "59.98"
            }
            response = requests.put(f"{self.api_endpoint}/carts/{cart_id}/items", json=update_data)
            success = response.status_code == 200
            self.log_test_result('Carts', 'PUT', f'/carts/{cart_id}/items', response.status_code, success, 
                               response.text, f"cart_id: {cart_id}")

            # CLEAR Cart
            response = requests.delete(f"{self.api_endpoint}/carts/{cart_id}")
            success = response.status_code == 200
            self.log_test_result('Carts', 'DELETE', f'/carts/{cart_id}', response.status_code, success, 
                               response.text, f"cart_id: {cart_id}")

    def test_orders_api(self):
        """Test all Order API endpoints"""
        # CREATE Order
        order_data = {
            "customer_id": "test_customer_123",
            "items": [{"product_id": "prod_001", "quantity": "1"}],
            "total_amount": "29.99",
            "status": "pending"
        }
        response = requests.post(f"{self.api_endpoint}/orders", json=order_data)
        success = response.status_code == 201
        order_id = response.json().get('order_id') if success else None
        if order_id:
            self.created_resources['order_id'] = order_id
        self.log_test_result('Orders', 'POST', '/orders', response.status_code, success, 
                           response.text, f"order_id: {order_id}")

        # GET All Orders
        response = requests.get(f"{self.api_endpoint}/orders")
        success = response.status_code == 200
        self.log_test_result('Orders', 'GET', '/orders', response.status_code, success, 
                           f"Retrieved {len(response.json()) if success else 0} orders")

        if order_id:
            # GET Order by ID
            response = requests.get(f"{self.api_endpoint}/orders/{order_id}")
            success = response.status_code == 200
            self.log_test_result('Orders', 'GET', f'/orders/{order_id}', response.status_code, success, 
                               response.text, f"order_id: {order_id}")

            # UPDATE Order Status
            update_data = {"status": "shipped", "tracking_number": "TRK123456"}
            response = requests.put(f"{self.api_endpoint}/orders/{order_id}/status", json=update_data)
            success = response.status_code == 200
            self.log_test_result('Orders', 'PUT', f'/orders/{order_id}/status', response.status_code, success, 
                               response.text, f"order_id: {order_id}")

        # GET Customer Orders
        response = requests.get(f"{self.api_endpoint}/orders/customer/test_customer_123")
        success = response.status_code == 200
        self.log_test_result('Orders', 'GET', '/orders/customer/test_customer_123', response.status_code, success, 
                           response.text, "customer_id: test_customer_123")

    def test_parameters_api(self):
        """Test all Parameter API endpoints"""
        # CREATE Parameter
        param_data = {
            "name": "test_parameter",
            "value": "test_value",
            "description": "Test parameter for API testing"
        }
        response = requests.post(f"{self.api_endpoint}/parameters", json=param_data)
        success = response.status_code == 201
        param_id = response.json().get('id') if success else None
        if param_id:
            self.created_resources['param_id'] = param_id
        self.log_test_result('Parameters', 'POST', '/parameters', response.status_code, success, 
                           response.text, f"id: {param_id}")

        # GET All Parameters
        response = requests.get(f"{self.api_endpoint}/parameters")
        success = response.status_code == 200
        self.log_test_result('Parameters', 'GET', '/parameters', response.status_code, success, 
                           f"Retrieved {len(response.json()) if success else 0} parameters")

        if param_id:
            # GET Parameter by ID
            response = requests.get(f"{self.api_endpoint}/parameters/{param_id}")
            success = response.status_code == 200
            self.log_test_result('Parameters', 'GET', f'/parameters/{param_id}', response.status_code, success, 
                               response.text, f"id: {param_id}")

            # UPDATE Parameter
            update_data = {"value": "updated_test_value", "description": "Updated test parameter"}
            response = requests.put(f"{self.api_endpoint}/parameters/{param_id}", json=update_data)
            success = response.status_code == 200
            self.log_test_result('Parameters', 'PUT', f'/parameters/{param_id}', response.status_code, success, 
                               response.text, f"id: {param_id}")

        # GET Parameter by Name (test with existing parameter)
        response = requests.get(f"{self.api_endpoint}/parameters/name/regio")
        success = response.status_code == 200
        self.log_test_result('Parameters', 'GET', '/parameters/name/regio', response.status_code, success, 
                           response.text, "name: regio")
        
        # GET Parameter by Name (test with created parameter)
        response = requests.get(f"{self.api_endpoint}/parameters/name/test_parameter")
        success = response.status_code == 200
        self.log_test_result('Parameters', 'GET', '/parameters/name/test_parameter', response.status_code, success, 
                           response.text, "name: test_parameter")

        if param_id:
            # DELETE Parameter
            response = requests.delete(f"{self.api_endpoint}/parameters/{param_id}")
            success = response.status_code == 200
            self.log_test_result('Parameters', 'DELETE', f'/parameters/{param_id}', response.status_code, success, 
                               response.text, f"id: {param_id}")

    def test_cognito_admin_api(self):
        """Test all Cognito Admin API endpoints"""
        test_username = f"testuser_{uuid.uuid4().hex[:8]}@hdcn-test.nl"
        test_group = f"testgroup_{uuid.uuid4().hex[:8]}"
        
        # GET User Pool Info
        response = requests.get(f"{self.api_endpoint}/cognito/pool")
        success = response.status_code == 200
        self.log_test_result('Cognito', 'GET', '/cognito/pool', response.status_code, success, 
                           response.text, "User pool info")

        # GET All Users
        response = requests.get(f"{self.api_endpoint}/cognito/users")
        success = response.status_code == 200
        self.log_test_result('Cognito', 'GET', '/cognito/users', response.status_code, success, 
                           f"Retrieved users" if success else response.text, "List all users")

        # GET All Groups
        response = requests.get(f"{self.api_endpoint}/cognito/groups")
        success = response.status_code == 200
        self.log_test_result('Cognito', 'GET', '/cognito/groups', response.status_code, success, 
                           f"Retrieved groups" if success else response.text, "List all groups")

        # CREATE Group
        group_data = {
            "groupName": test_group,
            "description": "Test group for API testing"
        }
        response = requests.post(f"{self.api_endpoint}/cognito/groups", json=group_data)
        success = response.status_code == 201
        if success:
            self.created_resources['test_group'] = test_group
        self.log_test_result('Cognito', 'POST', '/cognito/groups', response.status_code, success, 
                           response.text, f"groupName: {test_group}")

        # CREATE User
        user_data = {
            "username": test_username,
            "email": test_username,
            "tempPassword": "TestPass123!",
            "attributes": {
                "given_name": "Test",
                "family_name": "User"
            }
        }
        response = requests.post(f"{self.api_endpoint}/cognito/users", json=user_data)
        success = response.status_code == 201
        if success:
            self.created_resources['test_user'] = test_username
        self.log_test_result('Cognito', 'POST', '/cognito/users', response.status_code, success, 
                           response.text, f"username: {test_username}")

        if success and test_group in self.created_resources.get('test_group', ''):
            # ADD User to Group
            response = requests.post(f"{self.api_endpoint}/cognito/users/{test_username}/groups/{test_group}")
            success_add = response.status_code == 200
            self.log_test_result('Cognito', 'POST', f'/cognito/users/{test_username}/groups/{test_group}', 
                               response.status_code, success_add, response.text, 
                               f"username: {test_username}, group: {test_group}")

            # GET User's Groups
            response = requests.get(f"{self.api_endpoint}/cognito/users/{test_username}/groups")
            success_groups = response.status_code == 200
            self.log_test_result('Cognito', 'GET', f'/cognito/users/{test_username}/groups', 
                               response.status_code, success_groups, response.text, 
                               f"username: {test_username}")

            # GET Users in Group
            response = requests.get(f"{self.api_endpoint}/cognito/groups/{test_group}/users")
            success_group_users = response.status_code == 200
            self.log_test_result('Cognito', 'GET', f'/cognito/groups/{test_group}/users', 
                               response.status_code, success_group_users, response.text, 
                               f"groupName: {test_group}")

            # UPDATE User Attributes
            update_data = {
                "attributes": {
                    "given_name": "Updated Test",
                    "family_name": "Updated User"
                }
            }
            response = requests.put(f"{self.api_endpoint}/cognito/users/{test_username}", json=update_data)
            success_update = response.status_code == 200
            self.log_test_result('Cognito', 'PUT', f'/cognito/users/{test_username}', 
                               response.status_code, success_update, response.text, 
                               f"username: {test_username}")

            # REMOVE User from Group
            response = requests.delete(f"{self.api_endpoint}/cognito/users/{test_username}/groups/{test_group}")
            success_remove = response.status_code == 200
            self.log_test_result('Cognito', 'DELETE', f'/cognito/users/{test_username}/groups/{test_group}', 
                               response.status_code, success_remove, response.text, 
                               f"username: {test_username}, group: {test_group}")

            # DELETE User
            response = requests.delete(f"{self.api_endpoint}/cognito/users/{test_username}")
            success_del_user = response.status_code == 200
            self.log_test_result('Cognito', 'DELETE', f'/cognito/users/{test_username}', 
                               response.status_code, success_del_user, response.text, 
                               f"username: {test_username}")

            # DELETE Group
            response = requests.delete(f"{self.api_endpoint}/cognito/groups/{test_group}")
            success_del_group = response.status_code == 200
            self.log_test_result('Cognito', 'DELETE', f'/cognito/groups/{test_group}', 
                               response.status_code, success_del_group, response.text, 
                               f"groupName: {test_group}")

        # Test Bulk Operations
        # BULK Import Groups
        bulk_groups_data = {
            "groups": [
                {"groupName": "testBulkGroup1", "description": "Test bulk group 1"},
                {"groupName": "testBulkGroup2", "description": "Test bulk group 2"}
            ]
        }
        response = requests.post(f"{self.api_endpoint}/cognito/groups/import", json=bulk_groups_data)
        success = response.status_code == 201
        self.log_test_result('Cognito', 'POST', '/cognito/groups/import', response.status_code, success, 
                           response.text, "Bulk import groups")

        # Note: Bulk user import/assign operations available via direct Python scripts

        # Clean up bulk test resources
        for group in ["testBulkGroup1", "testBulkGroup2"]:
            requests.delete(f"{self.api_endpoint}/cognito/groups/{group}")

    def tearDown(self):
        """Clean up created resources and generate HTML report"""
        # Clean up remaining resources
        member_id = self.created_resources.get('member_id')
        if member_id:
            requests.delete(f"{self.api_endpoint}/members/{member_id}")
        
        payment_id = self.created_resources.get('payment_id')
        if payment_id:
            requests.delete(f"{self.api_endpoint}/payments/{payment_id}")

        # Generate HTML report
        self.generate_html_report()

    def generate_html_report(self):
        """Generate comprehensive HTML test report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>HDCN Backend API Test Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; padding: 15px; background-color: #e8f5e8; border-radius: 5px; }}
        .table-section {{ margin: 30px 0; }}
        .table-header {{ background-color: #333; color: white; padding: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .success {{ background-color: #d4edda; }}
        .failure {{ background-color: #f8d7da; }}
        .method {{ font-weight: bold; }}
        .endpoint {{ font-family: monospace; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>HDCN Backend API Test Results</h1>
        <p>Comprehensive testing of all 7 DynamoDB tables and their API endpoints</p>
        <p>Test executed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>API Endpoint: {self.api_endpoint}</p>
    </div>

    <div class="summary">
        <h2>Test Summary</h2>
        <p>Total Tests: {len(self.test_results)}</p>
        <p>Successful: {len([r for r in self.test_results if r['success']])}</p>
        <p>Failed: {len([r for r in self.test_results if not r['success']])}</p>
        <p>Success Rate: {(len([r for r in self.test_results if r['success']]) / len(self.test_results) * 100):.1f}%</p>
    </div>
"""

        # Group results by table
        tables = {}
        for result in self.test_results:
            table = result['table']
            if table not in tables:
                tables[table] = []
            tables[table].append(result)

        # Generate table sections
        for table_name, results in tables.items():
            html_content += f"""
    <div class="table-section">
        <div class="table-header">
            <h2>{table_name} Table - {len(results)} Tests</h2>
        </div>
        <table>
            <tr>
                <th>Method</th>
                <th>Endpoint</th>
                <th>Status Code</th>
                <th>Success</th>
                <th>Key Used</th>
                <th>Details</th>
            </tr>
"""
            for result in results:
                status_class = 'success' if result['success'] else 'failure'
                html_content += f"""
            <tr class="{status_class}">
                <td class="method">{result['method']}</td>
                <td class="endpoint">{result['endpoint']}</td>
                <td>{result['status_code']}</td>
                <td>{'PASS' if result['success'] else 'FAIL'}</td>
                <td>{result['key_used']}</td>
                <td>{result['details'][:100]}{'...' if len(result['details']) > 100 else ''}</td>
            </tr>
"""
            html_content += "        </table>\n    </div>\n"

        html_content += """
    <div class="table-section">
        <h2>API Endpoint Reference</h2>
        <table>
            <tr><th>Table</th><th>Primary Key</th><th>CRUD Operations</th></tr>
            <tr><td>Products</td><td>id</td><td>POST /insert-product/, GET /scan-product/, GET /getproduct-byid/{id}, PUT /update-product/{id}, DELETE /delete-product/{id}</td></tr>
            <tr><td>Members</td><td>id</td><td>POST /members, GET /members, GET /members/{id}, PUT /members/{id}, DELETE /members/{id}</td></tr>
            <tr><td>Payments</td><td>payment_id</td><td>POST /payments, GET /payments, GET /payments/{payment_id}, PUT /payments/{payment_id}, DELETE /payments/{payment_id}, GET /payments/member/{member_id}</td></tr>
            <tr><td>Events</td><td>event_id</td><td>POST /events, GET /events, GET /events/{event_id}, PUT /events/{event_id}, DELETE /events/{event_id}</td></tr>
            <tr><td>Memberships</td><td>membership_type_id</td><td>POST /memberships, GET /memberships, GET /memberships/{id}, PUT /memberships/{id}, DELETE /memberships/{id}</td></tr>
            <tr><td>Carts</td><td>cart_id</td><td>POST /carts, GET /carts/{cart_id}, PUT /carts/{cart_id}/items, DELETE /carts/{cart_id}</td></tr>
            <tr><td>Orders</td><td>order_id</td><td>POST /orders, GET /orders, GET /orders/{order_id}, PUT /orders/{order_id}/status, GET /orders/customer/{customer_id}</td></tr>
            <tr><td>Parameters</td><td>id</td><td>POST /parameters, GET /parameters, GET /parameters/{id}, GET /parameters/name/{name}, PUT /parameters/{id}, DELETE /parameters/{id}</td></tr>
            <tr><td>Cognito</td><td>username/groupName</td><td>14 endpoints: User CRUD, Group CRUD, User-Group management, Group import, Pool info</td></tr>
        </table>
    </div>
</body>
</html>
"""

        # Write HTML report to integration folder
        report_path = os.path.join(os.path.dirname(__file__), 'api_test_results.html')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n📊 HTML test report generated: {report_path}")
        print(f"📈 Test Summary: {len([r for r in self.test_results if r['success']])}/{len(self.test_results)} tests passed")
        print(f"📁 Report saved to: tests/integration/api_test_results.html")

    def test_all_apis(self):
        """Run all API tests in sequence"""
        print("🚀 Starting comprehensive API tests...")
        
        self.test_products_api()
        self.test_members_api()
        self.test_payments_api()
        self.test_events_api()
        self.test_memberships_api()
        self.test_carts_api()
        self.test_orders_api()
        self.test_parameters_api()
        self.test_cognito_admin_api()
        
        # Clean up remaining resources
        member_id = self.created_resources.get('member_id')
        if member_id:
            requests.delete(f"{self.api_endpoint}/members/{member_id}")
        
        payment_id = self.created_resources.get('payment_id')
        if payment_id:
            requests.delete(f"{self.api_endpoint}/payments/{payment_id}")
        
        # Generate HTML report
        print(f"📊 Generating HTML report with {len(self.test_results)} test results...")
        self.generate_html_report()
        
        print("✅ All API tests completed!")