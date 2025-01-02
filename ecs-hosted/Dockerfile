# Use Amazon Linux 2 base image for AWS Lambda
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR .

# Copy the requirements file and application code to the container
COPY . .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the app runs on
EXPOSE 5000

# Define the command to run the application
CMD ["gunicorn", "-b", "0.0.0.0:5000", "ecs_model_serve_main:app"]