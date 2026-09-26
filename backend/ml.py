from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import math
import os
import json
from typing import List, Optional
import random
from typing import List, Dict, Any
from datetime import timedelta
from typing import Any, Dict, List, Tuple


# --- ml/models/base.py ---
class BaseModel(ABC):
    """
    Abstract Base Class for Restaurant Combo Intelligence Machine Learning Models.
    Enforces unified fit, predict, evaluate, serialize, and deserialize interfaces.
    """

    def __init__(self, model_type: str = "BaseModel"):
        self.model_type = model_type
        self.feature_names: List[str] = []
        self.is_fitted: bool = False

    @abstractmethod
    def fit(self, X: List[List[float]], y: List[float], feature_names: Optional[List[str]] = None) -> "BaseModel":
        """Fits model parameters to historical training data."""
        pass

    @abstractmethod
    def predict(self, X: List[List[float]]) -> List[float]:
        """Predicts future target metric (e.g. combo sales frequency or revenue)."""
        pass

    def evaluate(self, X: List[List[float]], y: List[float]) -> Dict[str, float]:
        """Calculates standard regression and ranking metrics."""
        preds = self.predict(X)
        return calculate_metrics(y, preds)

    @abstractmethod
    def save(self, filepath: str) -> None:
        """Serializes model weights and feature definitions to disk."""
        pass

    @abstractmethod
    def load(self, filepath: str) -> "BaseModel":
        """Restores model weights from disk."""
        pass

# --- ml/models/combo_regressor.py ---
# Try importing XGBoost or Scikit-Learn
HAS_XGBOOST = False
HAS_SKLEARN = False

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    pass

try:
    from sklearn.ensemble import HistGradientBoostingRegressor
    HAS_SKLEARN = True
except ImportError:
    pass

class SimpleDecisionStump:
    """
    Lightweight decision stump used for Gradient Boosting Regression fallback.
    """
    def __init__(self):
        self.feature_idx: int = 0
        self.threshold: float = 0.0
        self.left_val: float = 0.0
        self.right_val: float = 0.0

    def fit(self, X: List[List[float]], residuals: List[float]):
        n_samples = len(X)
        if n_samples == 0:
            return
        n_features = len(X[0])
        best_loss = float("inf")

        for f_idx in range(n_features):
            vals = [row[f_idx] for row in X]
            thresholds = sorted(list(set(vals)))
            # Sample thresholds to keep fitting fast
            if len(thresholds) > 10:
                step = len(thresholds) // 10
                thresholds = thresholds[::step]

            for th in thresholds:
                left = [residuals[i] for i in range(n_samples) if X[i][f_idx] <= th]
                right = [residuals[i] for i in range(n_samples) if X[i][f_idx] > th]

                if not left or not right:
                    continue

                l_mean = sum(left) / len(left)
                r_mean = sum(right) / len(right)

                loss = sum((y - l_mean) ** 2 for y in left) + sum((y - r_mean) ** 2 for y in right)
                if loss < best_loss:
                    best_loss = loss
                    self.feature_idx = f_idx
                    self.threshold = th
                    self.left_val = l_mean
                    self.right_val = r_mean

    def predict_one(self, row: List[float]) -> float:
        return self.left_val if row[self.feature_idx] <= self.threshold else self.right_val

class PurePythonGradientBoostingRegressor:
    """
    Pure-Python Gradient Boosting Regressor ensuring 100% testable & executable
    regression without external binary compiler dependencies.
    """
    def __init__(self, n_estimators: int = 30, learning_rate: float = 0.1):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.base_val = 0.0
        self.trees: List[SimpleDecisionStump] = []

    def fit(self, X: List[List[float]], y: List[float]):
        if not X or not y:
            return
        self.base_val = sum(y) / len(y)
        residuals = [val - self.base_val for val in y]

        for _ in range(self.n_estimators):
            stump = SimpleDecisionStump()
            stump.fit(X, residuals)
            self.trees.append(stump)
            for i in range(len(residuals)):
                pred = stump.predict_one(X[i])
                residuals[i] -= self.learning_rate * pred

    def predict(self, X: List[List[float]]) -> List[float]:
        preds = []
        for row in X:
            val = self.base_val
            for tree in self.trees:
                val += self.learning_rate * tree.predict_one(row)
            preds.append(max(0.0, val)) # purchase count >= 0
        return preds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_val": self.base_val,
            "learning_rate": self.learning_rate,
            "trees": [
                {
                    "feature_idx": t.feature_idx,
                    "threshold": t.threshold,
                    "left_val": t.left_val,
                    "right_val": t.right_val,
                }
                for t in self.trees
            ],
        }

    def from_dict(self, d: Dict[str, Any]):
        self.base_val = d["base_val"]
        self.learning_rate = d["learning_rate"]
        self.trees = []
        for td in d["trees"]:
            st = SimpleDecisionStump()
            st.feature_idx = td["feature_idx"]
            st.threshold = td["threshold"]
            st.left_val = td["left_val"]
            st.right_val = td["right_val"]
            self.trees.append(st)

class ComboRegressor:
    """
    Phase 2 Combo Future Purchase Regressor.
    Priority: XGBoost -> HistGradientBoosting -> PurePythonGradientBoosting.
    """
    def __init__(self, feature_names: List[str]):
        self.feature_names = feature_names
        self.model_type = "XGBoostRegressor" if HAS_XGBOOST else ("HistGradientBoostingRegressor" if HAS_SKLEARN else "GradientBoostingRegressor")
        self.model = None

    def fit(self, X: List[List[float]], y: List[float]):
        if HAS_XGBOOST:
            self.model = xgb.XGBRegressor(
                n_estimators=60,
                max_depth=4,
                learning_rate=0.08,
                random_state=42,
                verbosity=0
            )
            self.model.fit(X, y)
        elif HAS_SKLEARN:
            self.model = HistGradientBoostingRegressor(
                max_iter=60,
                max_depth=4,
                learning_rate=0.08,
                random_state=42
            )
            self.model.fit(X, y)
        else:
            self.model = PurePythonGradientBoostingRegressor(n_estimators=35, learning_rate=0.1)
            self.model.fit(X, y)

    def predict(self, X: List[List[float]]) -> List[float]:
        if self.model is None:
            return [0.0] * len(X)

        if not isinstance(self.model, PurePythonGradientBoostingRegressor):
            raw_preds = self.model.predict(X)
            return [max(0.0, float(p)) for p in raw_preds]
        return self.model.predict(X)

    def save(self, file_path: str):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if not isinstance(self.model, PurePythonGradientBoostingRegressor):
            import joblib
            joblib.dump({"model": self.model, "features": self.feature_names, "type": self.model_type}, file_path)
            return

        data = {
            "model_type": self.model_type,
            "feature_names": self.feature_names,
            "state": self.model.to_dict() if hasattr(self.model, "to_dict") else {},
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, file_path: str) -> "ComboRegressor":
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Model file {file_path} not found")

        # Try joblib if exists
        try:
            import joblib
            obj = joblib.load(file_path)
            if isinstance(obj, dict) and "features" in obj:
                inst = cls(obj["features"])
                inst.model = obj["model"]
                inst.model_type = obj.get("type", "XGBoostRegressor")
                return inst
        except Exception:
            pass

        # Load from JSON
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        inst = cls(data["feature_names"])
        inst.model_type = data.get("model_type", "GradientBoostingRegressor")
        tree_model = PurePythonGradientBoostingRegressor()
        tree_model.from_dict(data.get("state", {}))
        inst.model = tree_model
        return inst

# --- ml/models/gradient_boosting.py ---
class GradientBoostingModel(BaseModel):
    """
    Gradient Boosting Decision Tree Regressor for Restaurant Combo Demand Prediction.
    Captures non-linear co-occurrence, seasonal shifts, and price sensitivity.
    """

    def __init__(self, n_estimators: int = 40, learning_rate: float = 0.08):
        super().__init__(model_type="GradientBoostingRegressor")
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.model = PurePythonGradientBoostingRegressor(n_estimators=n_estimators, learning_rate=learning_rate)

    def fit(self, X: List[List[float]], y: List[float], feature_names: Optional[List[str]] = None) -> "GradientBoostingModel":
        if feature_names:
            self.feature_names = feature_names
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: List[List[float]]) -> List[float]:
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predict.")
        return self.model.predict(X)

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = {
            "model_type": self.model_type,
            "feature_names": self.feature_names,
            "base_val": self.model.base_val,
            "learning_rate": self.model.learning_rate,
            "trees": [
                {
                    "feature_idx": t.feature_idx,
                    "threshold": t.threshold,
                    "left_val": t.left_val,
                    "right_val": t.right_val
                }
                for t in self.model.trees
            ]
        }
        with open(filepath, "w") as f:
            json.dump(data, f)

    def load(self, filepath: str) -> "GradientBoostingModel":
        with open(filepath, "r") as f:
            data = json.load(f)
        self.feature_names = data.get("feature_names", [])
        self.model.base_val = data.get("base_val", 0.0)
        self.model.learning_rate = data.get("learning_rate", 0.08)
        self.model.trees = []
        for t_dict in data.get("trees", []):
            stump = SimpleDecisionStump()
            stump.feature_idx = t_dict["feature_idx"]
            stump.threshold = t_dict["threshold"]
            stump.left_val = t_dict["left_val"]
            stump.right_val = t_dict["right_val"]
            self.model.trees.append(stump)
        self.is_fitted = True
        return self

# --- ml/models/linear_baseline.py ---
class LinearBaselineModel(BaseModel):
    """
    Linear Regression Baseline with L2 regularization (Ridge) for baseline benchmarking.
    Ensures model evaluation can prove non-linear tree models beat the baseline.
    """

    def __init__(self, alpha: float = 1.0, learning_rate: float = 0.01, max_iter: int = 100):
        super().__init__(model_type="LinearBaselineRegressor")
        self.alpha = alpha
        self.learning_rate = learning_rate
        self.max_iter = max_iter
        self.weights: List[float] = []
        self.bias: float = 0.0

    def fit(self, X: List[List[float]], y: List[float], feature_names: Optional[List[str]] = None) -> "LinearBaselineModel":
        if feature_names:
            self.feature_names = feature_names
        n_samples = len(X)
        if n_samples == 0:
            return self
        n_features = len(X[0])

        self.weights = [0.0] * n_features
        self.bias = sum(y) / n_samples

        # Gradient descent optimization
        for _ in range(self.max_iter):
            d_w = [0.0] * n_features
            d_b = 0.0
            for i in range(n_samples):
                pred = self.bias + sum(w * x for w, x in zip(self.weights, X[i]))
                err = pred - y[i]
                d_b += err
                for j in range(n_features):
                    d_w[j] += err * X[i][j]

            # Update with L2 regularization
            self.bias -= (self.learning_rate / n_samples) * d_b
            for j in range(n_features):
                self.weights[j] -= (self.learning_rate / n_samples) * (d_w[j] + self.alpha * self.weights[j])

        self.is_fitted = True
        return self

    def predict(self, X: List[List[float]]) -> List[float]:
        if not self.is_fitted:
            return [0.0 for _ in X]
        preds = []
        for row in X:
            val = self.bias + sum(w * x for w, x in zip(self.weights, row))
            preds.append(max(0.0, val))
        return preds

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = {
            "model_type": self.model_type,
            "feature_names": self.feature_names,
            "weights": self.weights,
            "bias": self.bias,
        }
        with open(filepath, "w") as f:
            json.dump(data, f)

    def load(self, filepath: str) -> "LinearBaselineModel":
        with open(filepath, "r") as f:
            data = json.load(f)
        self.feature_names = data.get("feature_names", [])
        self.weights = data.get("weights", [])
        self.bias = data.get("bias", 0.0)
        self.is_fitted = True
        return self

# --- ml/models/random_forest.py ---
class RandomForestModel(BaseModel):
    """
    Random Forest Regressor ensemble for Combo Demand Prediction.
    Fits diverse stumps on bootstrap sub-samples and feature subsets.
    """

    def __init__(self, n_estimators: int = 30):
        super().__init__(model_type="RandomForestRegressor")
        self.n_estimators = n_estimators
        self.trees: List[SimpleDecisionStump] = []

    def fit(self, X: List[List[float]], y: List[float], feature_names: Optional[List[str]] = None) -> "RandomForestModel":
        if feature_names:
            self.feature_names = feature_names
        n_samples = len(X)
        if n_samples == 0:
            return self

        self.trees = []
        for _ in range(self.n_estimators):
            # Bootstrap sample
            indices = [random.randint(0, n_samples - 1) for _ in range(n_samples)]
            sample_X = [X[i] for i in indices]
            sample_y = [y[i] for i in indices]

            stump = SimpleDecisionStump()
            stump.fit(sample_X, sample_y)
            self.trees.append(stump)

        self.is_fitted = True
        return self

    def predict(self, X: List[List[float]]) -> List[float]:
        if not self.is_fitted or not self.trees:
            return [0.0 for _ in X]
        preds = []
        for row in X:
            tree_preds = [t.predict_one(row) for t in self.trees]
            preds.append(max(0.0, sum(tree_preds) / len(tree_preds)))
        return preds

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = {
            "model_type": self.model_type,
            "feature_names": self.feature_names,
            "trees": [
                {
                    "feature_idx": t.feature_idx,
                    "threshold": t.threshold,
                    "left_val": t.left_val,
                    "right_val": t.right_val
                }
                for t in self.trees
            ]
        }
        with open(filepath, "w") as f:
            json.dump(data, f)

    def load(self, filepath: str) -> "RandomForestModel":
        with open(filepath, "r") as f:
            data = json.load(f)
        self.feature_names = data.get("feature_names", [])
        self.trees = []
        for t_dict in data.get("trees", []):
            stump = SimpleDecisionStump()
            stump.feature_idx = t_dict["feature_idx"]
            stump.threshold = t_dict["threshold"]
            stump.left_val = t_dict["left_val"]
            stump.right_val = t_dict["right_val"]
            self.trees.append(stump)
        self.is_fitted = True
        return self

# --- ml/utils/metrics.py ---
def calculate_mae(y_true: List[float], y_pred: List[float]) -> float:
    """Mean Absolute Error"""
    if not y_true or len(y_true) != len(y_pred):
        return 0.0
    return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / len(y_true)

def calculate_rmse(y_true: List[float], y_pred: List[float]) -> float:
    """Root Mean Squared Error"""
    if not y_true or len(y_true) != len(y_pred):
        return 0.0
    mse = sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / len(y_true)
    return math.sqrt(mse)

def calculate_mape(y_true: List[float], y_pred: List[float]) -> float:
    """Mean Absolute Percentage Error (handling 0 targets smoothly)"""
    if not y_true or len(y_true) != len(y_pred):
        return 0.0
    valid_pairs = [(t, p) for t, p in zip(y_true, y_pred) if abs(t) > 1e-4]
    if not valid_pairs:
        return 0.0
    return (sum(abs(t - p) / t for t, p in valid_pairs) / len(valid_pairs)) * 100.0

def calculate_r2(y_true: List[float], y_pred: List[float]) -> float:
    """Coefficient of Determination R^2"""
    if not y_true or len(y_true) < 2:
        return 0.0
    mean_y = sum(y_true) / len(y_true)
    ss_tot = sum((y - mean_y) ** 2 for y in y_true)
    if ss_tot == 0.0:
        return 1.0
    ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
    return max(-1.0, 1.0 - (ss_res / ss_tot))

def calculate_precision_at_k(y_true: List[float], y_pred: List[float], k: int = 10) -> float:
    """
    Precision@K: Top K predicted combos that actually fall into the top K real performers.
    """
    n = len(y_true)
    if n == 0:
        return 0.0
    k = min(k, n)
    if k == 0:
        return 0.0

    # Indices sorted by true descending
    true_top_k_indices = set(sorted(range(n), key=lambda i: y_true[i], reverse=True)[:k])
    # Indices sorted by pred descending
    pred_top_k_indices = set(sorted(range(n), key=lambda i: y_pred[i], reverse=True)[:k])

    intersection = true_top_k_indices.intersection(pred_top_k_indices)
    return round(len(intersection) / k, 4)

def calculate_metrics(y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
    """Computes all evaluation metrics required by Phase 2 Model Registry."""
    return {
        "mae": round(calculate_mae(y_true, y_pred), 3),
        "rmse": round(calculate_rmse(y_true, y_pred), 3),
        "mape": round(calculate_mape(y_true, y_pred), 2),
        "r2": round(calculate_r2(y_true, y_pred), 3),
        "precision_at_5": calculate_precision_at_k(y_true, y_pred, k=5),
        "precision_at_10": calculate_precision_at_k(y_true, y_pred, k=10),
    }

# --- ml/utils/time_split.py ---
def time_based_train_val_test_split(
    dataset: List[Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    target_window_days: int = 7,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split by observation-date groups and purge rows whose targets cross a split boundary."""
    if not 0 < train_ratio < 1 or not 0 < val_ratio < 1 or train_ratio + val_ratio >= 1:
        raise ValueError("train_ratio and val_ratio must be positive and sum to less than one")
    if target_window_days < 1:
        raise ValueError("target_window_days must be positive")
    if not dataset:
        return [], [], []

    sorted_data = sorted(dataset, key=lambda row: row["observation_date"])
    dates = sorted({row["observation_date"] for row in sorted_data})
    if len(dates) < 3:
        return sorted_data, [], []

    train_end = max(1, min(len(dates) - 2, int(len(dates) * train_ratio)))
    validation_end = max(train_end + 1, min(len(dates) - 1, int(len(dates) * (train_ratio + val_ratio))))
    train_dates = set(dates[:train_end])
    validation_dates = set(dates[train_end:validation_end])
    test_dates = set(dates[validation_end:])

    validation_start = min(validation_dates)
    test_start = min(test_dates)

    def target_ends_before(row: Dict[str, Any], boundary: Any) -> bool:
        target_end = row.get("target_end_date")
        if target_end is None:
            target_end = row["observation_date"] + timedelta(days=target_window_days)
        return target_end <= boundary

    train = [
        row for row in sorted_data
        if row["observation_date"] in train_dates and target_ends_before(row, validation_start)
    ]
    validation = [
        row for row in sorted_data
        if row["observation_date"] in validation_dates and target_ends_before(row, test_start)
    ]
    test = [row for row in sorted_data if row["observation_date"] in test_dates]
    return train, validation, test

__all__ = ['BaseModel', 'HAS_XGBOOST', 'HAS_SKLEARN', 'SimpleDecisionStump', 'PurePythonGradientBoostingRegressor', 'ComboRegressor', 'GradientBoostingModel', 'LinearBaselineModel', 'RandomForestModel', 'calculate_mae', 'calculate_rmse', 'calculate_mape', 'calculate_r2', 'calculate_precision_at_k', 'calculate_metrics', 'time_based_train_val_test_split']
