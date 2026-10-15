import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from app.models.configuration import Asset, AssetTemplate

app = create_app()

with app.app_context():
    asset_count = Asset.query.count()
    template_count = AssetTemplate.query.count()
    print(f"Assets: {asset_count}")
    print(f"Templates: {template_count}")
    
    if asset_count > 0 and template_count > 0:
        print("VERIFICATION PASSED")
    else:
        print("VERIFICATION FAILED")
