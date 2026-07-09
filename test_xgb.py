import xgboost as xgb
from sklearn.base import is_classifier
from sklearn.ensemble import VotingClassifier

clf = xgb.XGBClassifier()
print("Is classifier:", is_classifier(clf))
try:
    vc = VotingClassifier(estimators=[('xgb', clf)])
    print("VotingClassifier accepted it!")
except Exception as e:
    print("VotingClassifier error:", e)
