#!/bin/bash

# Create a session
SESSION_ID=$(curl -X POST http://dcc-helper-949926840523.us-central1.run.app/apps/dcc-helper/users/u_123/sessions/s_123 \
  -H "Content-Type: application/json" \
  -d '{"key1": "value1", "key2": 42}' \
  | jq -r '.id')

# Print the session ID
echo "Session ID: $SESSION_ID"