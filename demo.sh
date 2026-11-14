#!/bin/bash
# Demo : modification -> branche -> push -> Merge Request
set -e
echo "1. Modification du code..."
sed -i 's/APP_VERSION = "\(.*\)"/APP_VERSION = "demo-'"$(date +%H%M%S)"'"/' app.py

echo "2. Commit et push..."
git checkout -b feature/demo-$(date +%s)
git add app.py
git commit -m "feat: update app version (demo)"
git push origin HEAD

echo "3. Ouvrir la Merge Request dans GitLab, attendre le test vert, puis fusionner."
echo "4. Apres fusion : build -> push Harbor -> scan -> deploy automatique."
echo "5. Verification : curl http://localhost:3000/health"
