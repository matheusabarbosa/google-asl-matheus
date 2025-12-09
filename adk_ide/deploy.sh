gcloud run deploy adk-demo-agent-crv3 \
  --source . \
  --port 8080 \
  --memory 2G \
  --project=qwiklabs-asl-03-4fafb71c2045 \
  --region=us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances qwiklabs-asl-03-4fafb71c2045:us-central1:adk-demo-session-service-v2 \
  --update-env-vars SERVE_WEB_INTERFACE=False,SESSION_SERVICE_URI=$SESSION_SERVICE_URI,GOOGLE_CLOUD_PROJECT=qwiklabs-asl-03-4fafb71c2045 \
  --clear-base-image
