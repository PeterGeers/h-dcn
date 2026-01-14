FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy auth layer (shared authentication utilities)
COPY auth-layer/ /opt/python/

# Copy Lambda function code
COPY app.py ${LAMBDA_TASK_ROOT}

# Set Python path to include auth layer
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}:/opt/python"

# Set the CMD to your handler
CMD ["app.lambda_handler"]