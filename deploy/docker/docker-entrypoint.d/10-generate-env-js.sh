#!/usr/bin/env sh
set -eu

ENV_JS_PATH="/usr/share/nginx/html/env.js"

BACKEND_URL="${BACKEND_URL:-}"

if [ -n "${BACKEND_URL}" ]; then
  # escape for JS double-quoted string
  BACKEND_URL_ESCAPED="$(printf '%s' "${BACKEND_URL}" | sed 's/\\/\\\\/g; s/\"/\\"/g')"
  BACKEND_URL_JS="\"${BACKEND_URL_ESCAPED}\""
else
  BACKEND_URL_JS="\"\""
fi

cat > "${ENV_JS_PATH}" <<EOF
window.__ENV = window.__ENV || {};
window.__ENV.BACKEND_URL = ${BACKEND_URL_JS};
EOF

