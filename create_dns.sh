#!/bin/bash

# Ganti dengan API Token Anda
API_TOKEN="YOUR_API_TOKEN_HERE"
ZONE_ID="366dd04666cfb9d5537574441de0b5ac"

# Create CNAME record
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "CNAME",
    "name": "siling-ai.my.id",
    "content": "'"b6fb3cba-b22b-41d4-ad25-5d953cb3c3c6.cfargotunnel.com"'",
    "ttl": 1,
    "proxied": true
  }'

echo ""
echo "DNS Record created!"
