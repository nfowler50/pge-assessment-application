import logging
from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from linear_regress_model_handler import LinearRegressModelHandler as lrmh
from auth import AuthVerifier

# Set up logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Intialize model outside of handler to reduce processing latency while warm
model = lrmh(logger)

app = Flask(__name__)

# Set up auth
authenticator = AuthVerifier()
app.config["JWT_SECRET_KEY"] = authenticator.secret
jwt = JWTManager(app)


@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    if username != "demo" or password != "password":
        logger.info("Failed login attempt.")
        return jsonify({"error": "Bad username or password"}), 401

    # Generate access token
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)


# Health check route
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200


# Define the prediction route
@app.route("/predict", methods=["GET"])
@jwt_required()
def predict():
    # Return error if model failed to load
    if model.model is None:
        logger.error("error: Model initialization failed.")
        return jsonify({"error": "Model is not available. Initialization failed."}), 500

    try:
        # Get input from event (query paramters)
        input_data = request.args.get("input", None)

        result = model.predict(input_data)

        return (
            jsonify(
                {
                    "prediction": result,
                }
            ),
            200,
        )

    except ValueError as e:
        # Log the error and return the response with the error message
        logger.error(f"Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        # Log any unexpected errors and return a generic error message
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred."}), 500


# Run the Flask app
if __name__ == "__main__":
    # Only run app.run() in development environments
    # In production, use Gunicorn instead
    if os.environ.get("FLASK_ENV") == None:
        app.run(host="0.0.0.0", port=5000)
