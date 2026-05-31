FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies required by WeasyPrint
RUN yum install -y \
    pango \
    pango-devel \
    gdk-pixbuf2 \
    cairo \
    cairo-gobject \
    gobject-introspection \
    libffi-devel \
    && yum clean all

# Copy shared auth layer into the image (Lambda Layers not supported with container images)
COPY layers/auth-layer/python/ ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
COPY handler/generate_order_pdf/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy handler code
COPY handler/generate_order_pdf/app.py ${LAMBDA_TASK_ROOT}/
COPY handler/generate_order_pdf/__init__.py ${LAMBDA_TASK_ROOT}/

CMD ["app.lambda_handler"]
