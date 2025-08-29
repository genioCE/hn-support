#!/usr/bin/env bash
set -euo pipefail
mkdir -p ./proxy/certs

DOMAIN=${1:-hn.local}
WILDCARD="*.${DOMAIN}"
CRT=./proxy/certs/${DOMAIN}.crt
KEY=./proxy/certs/${DOMAIN}.key

if command -v mkcert >/dev/null 2>&1; then
  echo "[mkcert] generating cert for ${WILDCARD} and ${DOMAIN}"
  mkcert -install "${WILDCARD}" "${DOMAIN}"
  # mkcert outputs files like _wildcard.${DOMAIN}+1.pem and-key.pem
  # Normalize names:
  CRT_SRC="_wildcard.${DOMAIN}+1.pem"
  KEY_SRC="_wildcard.${DOMAIN}+1-key.pem"
  [ -f "${CRT_SRC}" ] && [ -f "${KEY_SRC}" ] || { echo "mkcert output not found"; exit 1; }
  cp "${CRT_SRC}" "${CRT}"
  cp "${KEY_SRC}" "${KEY}"
  echo "Wrote ${CRT} and ${KEY}"
  exit 0
fi

echo "[openssl] mkcert not found; generating self-signed wildcard cert (untrusted by default)"
SUBJ="/C=US/ST=Local/L=Local/O=HN/OU=Dev/CN=${DOMAIN}"
openssl req -x509 -nodes -days 3650 -newkey rsa:2048   -keyout "${KEY}" -out "${CRT}"   -subj "${SUBJ}"   -addext "subjectAltName=DNS:${DOMAIN},DNS:${WILDCARD}"

echo "Wrote ${CRT} and ${KEY} (self-signed). Import the .crt into your OS trust store to avoid warnings."
