FROM python:3.9-alpine
# Set work directory
WORKDIR /app
COPY requirements.txt /app/
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Copy application files
COPY . /app/
# Expose port
EXPOSE 80
# Run the application
CMD ["python", "app.py"]