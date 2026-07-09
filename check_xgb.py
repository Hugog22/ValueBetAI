import xgboost as xgb
clf = xgb.XGBClassifier()
print("hasattr _estimator_type:", hasattr(clf, "_estimator_type"))
print("hasattr __sklearn_tags__:", hasattr(clf, "__sklearn_tags__"))
