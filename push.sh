#!/bin/bash
# Git Push Helper - Push changes to GitHub

cd "$(dirname "$0")"

echo "=========================================="
echo "  📤 Pushing to GitHub"
echo "=========================================="

git add .
git status

echo ""
echo "Commit message:"
read -r msg

if [ -z "$msg" ]; then
    msg="Update $(date +'%Y-%m-%d %H:%M')"
fi

git commit -m "$msg"
git push origin main

echo ""
echo "✅ Done! Check your repo at https://github.com/abamores/PhilDisaster"