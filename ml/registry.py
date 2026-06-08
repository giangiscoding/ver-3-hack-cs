"""
Model registry — các loại model ứng viên cho mỗi cluster + chọn tự động theo CV.

Ý tưởng (theo gợi ý: LightGBM chưa chắc tốt cho nhóm ít dữ liệu):
  Mỗi cluster THỬ nhiều loại model, chọn loại có CV MAE thấp nhất.
  - Nhóm nhiều dữ liệu (FULL): cây boosting hoặc tuyến tính đều tốt
  - Nhóm ít dữ liệu/nhiễu (L3_ONLY): model regularized mạnh thường tổng quát tốt hơn

Hỗ trợ SHAP cho cả tree (TreeExplainer) lẫn linear (đóng góp = coef × feature chuẩn hóa).
"""

from __future__ import annotations
import numpy as np
import lightgbm as lgb
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score

SEED = 42

_LGB_STRONG = dict(n_estimators=400, learning_rate=0.05, max_depth=6, num_leaves=63,
                   min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
                   reg_alpha=0.1, reg_lambda=1.0, random_state=SEED, verbose=-1)
_LGB_SMALL = dict(n_estimators=200, learning_rate=0.04, max_depth=3, num_leaves=8,
                  min_child_samples=30, subsample=0.8, colsample_bytree=0.8,
                  reg_alpha=0.3, reg_lambda=2.0, random_state=SEED, verbose=-1)
_CB_PARAMS = dict(iterations=400, learning_rate=0.05, depth=6, l2_leaf_reg=3.0,
                  random_seed=SEED, verbose=0, allow_writing_files=False, nan_mode="Min")

LINEAR_MODELS = {"ridge"}


def build(name: str):
    """Khởi tạo một model ứng viên theo tên."""
    if name == "lgbm_strong":
        return lgb.LGBMRegressor(**_LGB_STRONG)
    if name == "lgbm_small":
        return lgb.LGBMRegressor(**_LGB_SMALL)
    if name == "ridge":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=10.0))
    if name == "catboost":
        from catboost import CatBoostRegressor
        return CatBoostRegressor(**_CB_PARAMS)
    raise ValueError(f"Model không xác định: {name}")


CANDIDATES = ["lgbm_strong", "lgbm_small", "ridge", "catboost"]


def select_best(X, y, candidates=None, cv=5) -> tuple[str, float]:
    """Chọn loại model có CV MAE thấp nhất. Trả về (tên, cv_mae)."""
    candidates = candidates or CANDIDATES
    best_name, best_mae = None, float("inf")
    for name in candidates:
        try:
            scores = cross_val_score(build(name), X, y, cv=cv,
                                     scoring="neg_mean_absolute_error", n_jobs=-1)
            mae = -scores.mean()
        except Exception:
            continue
        if mae < best_mae:
            best_name, best_mae = name, mae
    return best_name, best_mae


def is_linear(name: str) -> bool:
    return name in LINEAR_MODELS


def shap_contributions(model, name: str, X_row, feature_cols: list[str]) -> np.ndarray:
    """
    Đóng góp từng feature vào dự đoán (SHAP-style), xử lý cả tree lẫn linear.
    X_row: DataFrame 1 hàng. Trả về mảng đóng góp theo thứ tự feature_cols.
    """
    if is_linear(name):
        # Linear: SHAP_i = coef_i × (x_i chuẩn hóa). StandardScaler đã center → baseline≈mean.
        pre = Pipeline(model.steps[:-1])      # imputer + scaler
        reg = model.steps[-1][1]              # Ridge
        Xt = pre.transform(X_row)[0]
        return reg.coef_ * Xt
    # Tree-based: TreeExplainer
    import shap
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X_row)
    return sv[0] if np.ndim(sv) > 1 else np.asarray(sv).ravel()
