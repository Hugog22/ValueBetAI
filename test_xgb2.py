import xgboost as xgb
from sklearn.base import is_classifier
from sklearn.ensemble import VotingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.datasets import make_classification

X, y = make_classification()
clf = xgb.XGBClassifier()
vc = VotingClassifier(estimators=[('xgb', clf)], voting='soft')
vc.fit(X, y)
cal = CalibratedClassifierCV(vc, cv=3)
try:
    cal.fit(X, y)
    print("CalibratedClassifierCV accepted it!")
except Exception as e:
    print("CalibratedClassifierCV error:", e)
