FROM public.ecr.aws/lambda/python:3.11

# Install pandas and pyarrow
RUN pip install --no-cache-dir pandas==2.0.3 pyarrow==12.0.1 boto3==1.34.0 numpy==1.24.3

# Copy shared authentication utilities
COPY shared/ ${LAMBDA_TASK_ROOT}/shared/

# Copy function code
COPY app.py ${LAMBDA_TASK_ROOT}/

# Command to run the Lambda function
CMD ["app.lambda_handler"]