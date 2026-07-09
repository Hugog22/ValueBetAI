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

    # Replace const API = process.env.NEXT_PUBLIC_API_URL... with const API = '/api/proxy';
    content = re.sub(
        r"(const API = process\.env\.NEXT_PUBLIC_API_URL \|\| 'http://localhost:8001';)",
        r"const API = '/api/proxy';",
        content
    )
    
    # Replace inline fetch literals
    content = re.sub(
        r"`\$\{process\.env\.NEXT_PUBLIC_API_URL \|\| 'http://localhost:8001'\}/api/",
        r"`/api/proxy/",
        content
    )

    # Remove Authorization: `Bearer ${token}` since middleware handles it
    # We should match headers objects and remove the Authorization line.
    content = re.sub(
        r"[\s]*Authorization:\s*`Bearer \$\{token\}`[\s]*,?",
        "",
        content
    )
    
    with open(file_path, "w") as f:
        f.write(content)

print("Replacement complete.")
