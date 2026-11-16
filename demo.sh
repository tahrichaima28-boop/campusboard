#!/bin/bash
# Démo : modification -> branche -> push -> Merge Request
set -e

echo "1. Modification du code (version de l'application)..."
NEW="demo-$(date +%H%M%S)"
sed -i "s/APP_VERSION = \".*\"/APP_VERSION = \"$NEW\"/" app.py

echo "2. Branche, commit et push..."
BRANCH="feature/demo-$(date +%s)"
git checkout -b "$BRANCH"
git add app.py
git commit -m "feat: update app version (demo)"
git push -u gitlab "$BRANCH"

echo "3. Ouvrir la Merge Request :"
echo "   http://localhost:8081/root/campusboard/-/merge_requests/new?merge_request%5Bsource_branch%5D=${BRANCH//\//%2F}"
echo "4. Attendre le test vert, fusionner, puis suivre le pipeline (build, scan, deploy)."
echo "5. Vérifier : curl http://localhost:3000/health   (version = $NEW)"
