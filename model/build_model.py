import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

# Step 1: Read data from a CSV file into a pandas DataFrame
file_path = "data.csv"  # Replace with your CSV file path
df = pd.read_csv(file_path)

# Step 2: Display the first few rows of the dataframe (optional)
print("Data Preview:")
print(df.head())

# Step 3: Prepare your data (assuming your CSV has columns 'X' and 'y')
# Replace 'X' with the column(s) you want as features and 'y' as the target variable
X = df[["GPA"]].values  # Features (replace 'X' with actual feature column name(s))
y = df["SAT"].values  # Target variable (replace 'y' with actual target column name)

# Step 4: Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Step 5: Train a Linear Regression model
model = LinearRegression()
model.fit(X_train, y_train)

# Step 6: Make predictions on the test set
y_pred = model.predict(X_test)

# Step 7: Evaluate the model (optional)
mse = mean_squared_error(y_test, y_pred)
print(f"Mean Squared Error: {mse}")

# Step 8: Display the model coefficients (optional)
print(f"Model Coefficients: {model.coef_}")
print(f"Model Intercept: {model.intercept_}")

model_filename = "linear_regression_model.pkl"  # File name for the pickle file
with open(model_filename, "wb") as f:
    pickle.dump(model, f)

print(f"Model exported to {model_filename}")
