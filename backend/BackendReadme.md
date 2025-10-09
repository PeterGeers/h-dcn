# HDCN Backend API

Comprehensive serverless backend API for HDCN (Harley-Davidson Club Nederland) built with AWS SAM, providing complete CRUD operations for club management.

## Project Structure

- `handler/` - Lambda function handlers for all API endpoints (51 total)
- `template.yaml` - SAM template defining AWS resources
- `api.md` - Complete API documentation
- `cognito-users.csv` - Sample user data for bulk import

## Features

### Core APIs (51 endpoints)
- **Products** - E-commerce product management
- **Members** - Club member management with full CRUD
- **Payments** - Payment tracking and member payment history
- **Events** - Club event management and participation
- **Memberships** - Membership type management with DynamoDB integration
- **Carts & Orders** - Shopping cart and order processing
- **Parameters** - System configuration and lookup data

### Cognito User Management
- Complete user pool administration
- Group management and user assignments
- Bulk user import from CSV with existence checking
- User/group relationship management

### Technical Features
- **Serverless Architecture** - AWS Lambda + API Gateway
- **DynamoDB Integration** - NoSQL data storage
- **CORS Support** - Cross-origin resource sharing enabled
- **Auto-generated IDs** - UUID generation for all entities
- **Timestamp Management** - Automatic created_at/updated_at fields
- **Minimal Business Logic** - Simple data storage operations

The application uses AWS Lambda functions, API Gateway, DynamoDB, and Cognito User Pools. All resources are defined in the `template.yaml` file.

## API Documentation

See `api.md` for complete API documentation including:
- All 51 endpoint specifications
- Request/response examples
- Authentication requirements
- Available system parameters

## Development Tools

Use the AWS Toolkit for your preferred IDE:
* [VS Code](https://docs.aws.amazon.com/toolkit-for-vscode/latest/userguide/welcome.html)
* [PyCharm](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [IntelliJ](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)

## Deploy the sample application

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

To build and deploy your application for the first time, run the following in your shell:

```bash
sam build --use-container
sam deploy --guided
```

The first command will build the source of your application. The second command will package and deploy your application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
* **AWS Region**: The AWS region you want to deploy your app to.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modifies IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.
* **Public API endpoints**: The API Gateway endpoints are publicly accessible. For production, consider adding authentication via Cognito or API keys.

You can find your API Gateway Endpoint URL in the output values displayed after deployment.

## Monitoring and Logs

View Lambda function logs:
```bash
sam logs -n CreateMemberFunction --stack-name python-crud-api --tail
sam logs -n HdcnCognitoAdminFunction --stack-name python-crud-api --tail
```

All functions support AWS X-Ray tracing for performance monitoring.

## Tests

Tests are defined in the `tests` folder in this project. Use PIP to install the test dependencies and run tests.

```bash
python-crud-api$ pip install -r tests/requirements.txt --user
# unit test
python-crud-api$ python -m pytest tests/unit -v
# integration test, requiring deploying the stack first.
# Create the env variable AWS_SAM_STACK_NAME with the name of the stack we are testing
python-crud-api$ AWS_SAM_STACK_NAME=<stack-name> python -m pytest tests/integration -v
```

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name python-crud-api
```

**Note**: This will delete all DynamoDB tables and data. Ensure you have backups if needed.

## Resources

## Architecture

- **API Gateway**: RESTful API endpoints with CORS
- **Lambda Functions**: 51 serverless functions for business logic
- **DynamoDB**: NoSQL database for all data storage
- **Cognito**: User pool management and authentication
- **IAM Roles**: Least-privilege access for Lambda functions

## Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [API Gateway CORS](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html)
