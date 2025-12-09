#!/bin/bash
# ACL API Testing with curl
# Replace localhost:5000 with your actual Flask server address

BASE_URL="http://localhost:5000"

echo "=== 1. Get all ACLs ==="
curl -X GET "${BASE_URL}/api/acls" | jq

echo -e "\n\n=== 2. Create a new ACL with multiple rules ==="
curl -X POST "${BASE_URL}/api/acl" \
  -H "Content-Type: application/json" \
  -d '{
    "tag": "test-acl",
    "rules": [
      {
        "action": "permit",
        "src_ip": "192.168.1.0",
        "src_prefix_len": 24,
        "dst_ip": "10.0.0.0",
        "dst_prefix_len": 8,
        "proto": 6,
        "src_port_min": 0,
        "src_port_max": 65535,
        "dst_port_min": 80,
        "dst_port_max": 80
      },
      {
        "action": "deny",
        "src_ip": "192.168.2.0",
        "src_prefix_len": 24,
        "dst_ip": "0.0.0.0",
        "dst_prefix_len": 0,
        "proto": 0,
        "src_port_min": 0,
        "src_port_max": 65535,
        "dst_port_min": 0,
        "dst_port_max": 65535
      }
    ]
  }' | jq

# Save the acl_index from the response for subsequent tests
ACL_INDEX=0  # Replace with actual index from response

echo -e "\n\n=== 3. Add a rule to existing ACL ==="
curl -X POST "${BASE_URL}/api/acl/${ACL_INDEX}/rule" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "permit",
    "src_ip": "172.16.0.0",
    "src_prefix_len": 16,
    "dst_ip": "8.8.8.8",
    "dst_prefix_len": 32,
    "proto": 17,
    "src_port_min": 53,
    "src_port_max": 53,
    "dst_port_min": 53,
    "dst_port_max": 53
  }' | jq

echo -e "\n\n=== 4. Edit rule at index 0 in ACL ==="
curl -X PUT "${BASE_URL}/api/acl/${ACL_INDEX}/rule/0" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "deny",
    "src_ip": "192.168.1.0",
    "src_prefix_len": 24,
    "proto": 6,
    "dst_port_min": 443,
    "dst_port_max": 443
  }' | jq

echo -e "\n\n=== 5. Get all ACLs (to see changes) ==="
curl -X GET "${BASE_URL}/api/acls" | jq

echo -e "\n\n=== 6. Get ACL-Interface mappings ==="
curl -X GET "${BASE_URL}/api/aclinterfaces" | jq

# Assuming you have a sw_if_index (e.g., 1)
SW_IF_INDEX=1

echo -e "\n\n=== 7. Attach ACL to interface (input) ==="
curl -X POST "${BASE_URL}/api/acl/${ACL_INDEX}/interface/${SW_IF_INDEX}" \
  -H "Content-Type: application/json" \
  -d '{
    "is_input": true
  }' | jq

echo -e "\n\n=== 8. Attach ACL to interface (output) ==="
curl -X POST "${BASE_URL}/api/acl/${ACL_INDEX}/interface/${SW_IF_INDEX}" \
  -H "Content-Type: application/json" \
  -d '{
    "is_input": false
  }' | jq

echo -e "\n\n=== 9. Get ACL-Interface mappings (after attachment) ==="
curl -X GET "${BASE_URL}/api/aclinterfaces" | jq

echo -e "\n\n=== 10. Detach ACL from interface (input) ==="
curl -X DELETE "${BASE_URL}/api/acl/${ACL_INDEX}/interface/${SW_IF_INDEX}" \
  -H "Content-Type: application/json" \
  -d '{
    "is_input": true
  }' | jq

echo -e "\n\n=== 11. Delete rule at index 1 from ACL ==="
curl -X DELETE "${BASE_URL}/api/acl/${ACL_INDEX}/rule/1" | jq

echo -e "\n\n=== 12. Get all ACLs (after rule deletion) ==="
curl -X GET "${BASE_URL}/api/acls" | jq

echo -e "\n\n=== 13. Delete ACL ==="
curl -X DELETE "${BASE_URL}/api/acl/${ACL_INDEX}" | jq

echo -e "\n\n=== 14. Get all ACLs (final check) ==="
curl -X GET "${BASE_URL}/api/acls" | jq

echo -e "\n\n=== Testing Complete ==="