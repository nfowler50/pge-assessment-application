# Use Amazon Linux 2 base image for AWS Lambda
FROM public.ecr.aws/lambda/python:3.12

# Copy your lambda function code to the container
COPY . ${LAMBDA_TASK_ROOT}

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the CMD to the handler in your Lambda function
CMD ["authenticator.handler"]