#!/usr/bin/env bash
# Upload Android signing values as GitHub Actions environment secrets via gh.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <keystore.p12> [OWNER/REPOSITORY]" >&2
  exit 2
fi
keystore="$1"
repo="${2:-}"

[[ -f "$keystore" ]] || { echo "Keystore not found: $keystore" >&2; exit 1; }
command -v gh >/dev/null 2>&1 || { echo 'GitHub CLI (gh) is required.' >&2; exit 1; }
command -v keytool >/dev/null 2>&1 || { echo 'keytool is required.' >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo 'python3 is required.' >&2; exit 1; }
gh auth status >/dev/null

if [[ -z "$repo" ]]; then
  repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
fi
if [[ ! "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo 'Repository must be OWNER/REPOSITORY.' >&2
  exit 2
fi

read -r -p 'Android key alias: ' alias
[[ -n "$alias" ]] || { echo 'Key alias cannot be empty.' >&2; exit 2; }
read -r -s -p 'Keystore password: ' store_password
echo
read -r -s -p 'Key password: ' key_password
echo
[[ -n "$store_password" && -n "$key_password" ]] || { echo 'Passwords cannot be empty.' >&2; exit 2; }

# Check the local keystore before transmitting any secret.
ANDROID_STORE_PASSWORD="$store_password" keytool -list \
  -keystore "$keystore" -storetype PKCS12 \
  -storepass:env ANDROID_STORE_PASSWORD -alias "$alias" >/dev/null

# Create the environment if needed. Configure required reviewers and branch/tag
# restrictions in GitHub Settings before using the signed-release workflow.
gh api --method PUT "repos/$repo/environments/android-release" --silent

python3 -c 'import base64,pathlib,sys; sys.stdout.buffer.write(base64.b64encode(pathlib.Path(sys.argv[1]).read_bytes()))' "$keystore" \
  | gh secret set ANDROID_KEYSTORE_BASE64 --app actions --repo "$repo" --env android-release
printf '%s' "$alias" \
  | gh secret set ANDROID_KEY_ALIAS --app actions --repo "$repo" --env android-release
printf '%s' "$store_password" \
  | gh secret set ANDROID_STORE_PASSWORD --app actions --repo "$repo" --env android-release
printf '%s' "$key_password" \
  | gh secret set ANDROID_KEY_PASSWORD --app actions --repo "$repo" --env android-release

unset store_password key_password
printf '\nUploaded Android signing secrets to %s / android-release.\n' "$repo"
printf 'Next, require reviewers and restrict deployment branches/tags in the android-release environment settings.\n'
