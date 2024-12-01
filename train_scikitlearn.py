import talib
import requests
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from candle_stick_analysis import fetch_historical_data


class Price_prediction_by_Ai:

    # 1. Prepare Data
    def prepare_data(candlestick_data):

        df = pd.DataFrame(candlestick_data)

        df['open'] = pd.to_numeric(df['open'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])

        # Feature Engineering (example)
        df['close_pct_change'] = df['close'].pct_change()
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)
        df['macd'], _, _ = talib.MACD(df['close'])
        # ... add more features (e.g., moving averages, Bollinger Bands, etc.)

        df.dropna(inplace=True)  # Remove rows with NaN values after calculating indicators

        # Target variable (example: predict if price goes up or down in the next candlestick)
        df['future_price_up'] = (df['close'].shift(-1) > df['close']).astype(int)

        X = df[['close_pct_change', 'rsi', 'macd']]  # Select features
        y = df['future_price_up']  # Target variable

        return train_test_split(X, y, test_size=0.2, random_state=42)

    # 2. Train Models
    def train_linear_regression(X_train, y_train):
        model = LinearRegression()
        model.fit(X_train, y_train)
        return model

    def train_logistic_regression(X_train, y_train):
        model = LogisticRegression()
        model.fit(X_train, y_train)
        return model

    def train_svm(X_train, y_train):
        model = SVR(
            kernel='linear')  # You can try different kernels like 'rbf'
        model.fit(X_train, y_train)
        return model

    # 3. Predict
    def predict_price_movement(model, current_features):
        """
        Predicts price movement using the given model and features.
        Handles NaN values and ensures correct dimensionality for different models.

        Args:
        model: The trained machine learning model.
        current_features: The features to use for prediction.

        Returns:
        The predicted price movement.
        """

        # Impute NaN values with the mean
        imputer = SimpleImputer(strategy='mean')  
        features = imputer.fit_transform(current_features)

        # Ensure features is in the correct shape for the model
        if isinstance(model, (LinearRegression, LogisticRegression, SVR)):  # 2D input
            features = features.reshape(1, -1)  # Reshape to 2D for these models
        else:
            # Add more conditions for other models as needed
            pass  


        prediction = model.predict(features)
        return prediction.flatten()[0]  # Flatten the prediction output
    

def transform_data(data, scaler):
    """
    Transforms data using a StandardScaler, ensuring 2D output.

    Args:
      data: A 1D, 2D, or 3D array-like object.
      scaler: A StandardScaler object.

    Returns:
      The transformed data as a 2D NumPy array.
    """

    if data is None or len(data) == 0:
        return np.array([[]])  # Return 2D empty array

    data = np.array(data)  # Convert to NumPy array

    # Always reshape to 2D before transforming
    data = data.reshape(1, -1)  # Reshape to 2D 

    transformed_data = scaler.transform(data)  # Transform the data

    # Ensure 2D output, even for single samples
    return transformed_data.reshape(1, -1)  
    


# def transform_data(data, scaler):
#     """
#     Transforms data using a StandardScaler, handling both 2D and 3D data.

#     Args:
#       data: A 2D or 3D array-like object containing the data to be transformed.
#       scaler: A StandardScaler object.

#     Returns:
#       The transformed data as a NumPy array, always reshaped to 2D. 
#     """

#     if data is None or len(data) == 0:  # Handle empty data
#         return np.array([[]])  # Return 2D empty array

#     data = np.array(data)  # Convert to NumPy array
#     original_shape = data.shape  # Store original shape

#     if data.ndim == 1:  # 1D data (single sample)
#         data = data.reshape(1, -1)  # Reshape to 2D
#     elif data.ndim == 2:  # 2D data (multiple samples)
#         pass  # No need to reshape
#     elif data.ndim == 3:  # 3D data (assume extra dimension of size 1)
#         data = data.reshape(-1, data.shape[-1])  # Reshape to 2D
#     else:
#         raise ValueError("Data must be 1D, 2D, or 3D.")

#     transformed_data = scaler.transform(data)  # Transform the data

#     # Ensure 2D output, even for single samples
#     if transformed_data.shape[0] == 1 and len(original_shape) == 1:  
#         transformed_data = transformed_data.reshape(1, -1) 

#     return transformed_data
    


# Example usage in your bot

# candlestick_data = fetch_historical_data("BTCUSDT","15m",100)

# X_train, X_test, y_train, y_test = prepare_data(candlestick_data)

# # Scale the data (important for SVM)
# scaler = StandardScaler()
# X_train = scaler.fit_transform(X_train)
# X_test = scaler.transform(X_test)

# # Train the models
# linear_model = train_linear_regression(X_train, y_train)
# logistic_model = train_logistic_regression(X_train, y_train)
# svm_model = train_svm(X_train, y_train)

# ... (in your analyze_all_gainers_order_book function) ...

# Get current features for prediction
# current_features = scaler.transform([[
#     historical_data[-1]['close_pct_change'],
#     technical_analysis['RSI14'],  # Or any other RSI period
#     technical_analysis['MACD_Line_cross_above_Signal']['cross_above']
# ]])  # Make sure features match the training data

# # Predict using each model
# linear_prediction = predict_price_movement(linear_model, current_features[0])
# logistic_prediction = predict_price_movement(logistic_model, current_features[0])
# svm_prediction = predict_price_movement(svm_model, current_features[0])

# Sample candlestick data (replace with your actual data)


# ... (use the predictions in your trading decision logic) ...

# print("linear_model: ", linear_model)

# print("logistic_model: ", logistic_model)

# print("svm_model: ", svm_model)