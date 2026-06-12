import sys
import logging
logging.basicConfig(level=logging.INFO)
sys.path.append('backend')

from core.cache_service import refresh_cache
try:
    refresh_cache()
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
