import os
import re

files_to_update = [
    "frontend/src/app/success/page.tsx",
    "frontend/src/app/dashboard/page.tsx",
    "frontend/src/app/register/page.tsx",
    "frontend/src/app/forgot-password/page.tsx",
    "frontend/src/app/reset-password/page.tsx",
    "frontend/src/app/bankroll/page.tsx",
    "frontend/src/components/ProtectedRoute.tsx",
    "frontend/src/components/BetModal.tsx",
    "frontend/src/components/MatchesDashboard.tsx",
]

for file_path in files_to_update:
    if not os.path.exists(file_path):
        continue
    
    with open(file_path, "r") as f:
        content = f.read()

    # Fix ${API}/api/
    content = content.replace("${API}/api/", "${API}/")
    content = content.replace("/api/proxy/api/", "/api/proxy/")

    # Remove ALL occurrences of: headers: { 'Authorization': `Bearer ${token}` }
    # Or variations
    content = re.sub(
        r"headers:\s*\{\s*'?Authorization'?\s*:\s*`Bearer \$\{token\}`\s*\},?",
        "",
        content
    )
    # If there are empty options objects due to header removal like `fetch(..., { \n })`, clean them up:
    content = re.sub(
        r",\s*\{\s*\}",
        "",
        content
    )

    with open(file_path, "w") as f:
        f.write(content)

print("Fix complete.")
