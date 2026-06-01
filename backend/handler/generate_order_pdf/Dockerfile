FROM public.ecr.aws/lambda/python:3.12

# Install system dependencies required by WeasyPrint
# Python 3.12 image is based on Amazon Linux 2023 (dnf, Pango 1.50+)
RUN dnf install -y \
    pango \
    gdk-pixbuf2 \
    cairo \
    cairo-gobject \
    gobject-introspection \
    libffi-devel \
    harfbuzz \
    fribidi \
    fontconfig \
    && dnf clean all

# Fix fontconfig cache directory for Lambda (read-only filesystem)
RUN mkdir -p /tmp/fontconfig-cache && \
    echo '<?xml version="1.0"?>' > /etc/fonts/local.conf && \
    echo '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">' >> /etc/fonts/local.conf && \
    echo '<fontconfig><cachedir>/tmp/fontconfig-cache</cachedir></fontconfig>' >> /etc/fonts/local.conf

# Copy shared auth layer into the image (Lambda Layers not supported with container images)
COPY layers/auth-layer/python/ ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
COPY handler/generate_order_pdf/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy handler code
COPY handler/generate_order_pdf/app.py ${LAMBDA_TASK_ROOT}/
COPY handler/generate_order_pdf/__init__.py ${LAMBDA_TASK_ROOT}/

CMD ["app.lambda_handler"]
