import azure.functions as func
import logging
from api import search, ask, health_check
import json
import os
import hmac
import hashlib
import time

app = func.FunctionApp()

def verify_slack_request(req: func.HttpRequest) -> bool:
    """
    Verify that the request is coming from Slack by checking the signature.
    
    Slack sends a signature in the X-Slack-Signature header, which is a hash of
    the request timestamp and body, signed with the Slack signing secret.
    This is used for the /ask endpoint when called from Slack.
    """
    # During challenge verification, we skip the signature check
    try:
        if "challenge" in req.get_json():
            return True
    except:
        pass
        
    # Get the Slack signing secret
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
    if not signing_secret:
        logging.warning("SLACK_SIGNING_SECRET environment variable not set")
        return False
        
    # Get the signature from the request
    slack_signature = req.headers.get("X-Slack-Signature")
    slack_timestamp = req.headers.get("X-Slack-Request-Timestamp")
    
    # Check if headers are present
    if not slack_signature or not slack_timestamp:
        logging.warning("Slack signature headers missing")
        return False
        
    # Check if the timestamp is recent to prevent replay attacks
    current_timestamp = int(time.time())
    if abs(current_timestamp - int(slack_timestamp)) > 60 * 5:
        logging.warning("Slack request timestamp is too old")
        return False
        
    # Get the request body as bytes
    body = req.get_body().decode("utf-8")
    
    # Create the base string (timestamp + ':' + body)
    base_string = f"v0:{slack_timestamp}:{body}"
    
    # Create the signature
    my_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        base_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(my_signature, slack_signature)

@app.function_name(name="search")
@app.route(route="search", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
async def search_function(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main search endpoint for the Vector Knowledge Engine.
    
    Accepts JSON payload with:
    - query: The search query string
    - top_k: Number of results to return (default: 5)
    - format: Response format ("json", "slack", "teams") (default: "json")
    
    Returns search results in the requested format.
    """
    try:
        body = req.get_json()
        response = await search(body)
        return func.HttpResponse(
            body=json.dumps(response),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Search function error: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )

@app.function_name(name="ask")
@app.route(route="ask", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
async def ask_function(req: func.HttpRequest) -> func.HttpResponse:
    """
    Platform-specific ask endpoint, primarily for Slack slash commands.
    
    Handles Slack's URL verification challenge and slash command requests.
    Can be extended for other chat platforms with similar webhook patterns.
    """
    try:
        # Check for Slack challenge (URL verification)
        try:
            body = req.get_json()
            if body and body.get("type") == "url_verification":
                return func.HttpResponse(
                    body=json.dumps({"challenge": body.get("challenge")}),
                    mimetype="application/json",
                    status_code=200
                )
        except ValueError:
            pass  # Not JSON data, continue with normal form handling
            
        # Get form data (typical for Slack slash commands)
        form_data = dict(req.form)
        
        # Extract required fields
        text = form_data.get("text", "")
        user_id = form_data.get("user_id", "")
        channel_id = form_data.get("channel_id", "")
        team_id = form_data.get("team_id", "")
        
        response = await ask(
            text=text,
            user_id=user_id,
            channel_id=channel_id,
            team_id=team_id
        )
        return func.HttpResponse(
            body=json.dumps(response),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Ask function error: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )

@app.function_name(name="health")
@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
async def health_function(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint for monitoring and deployment verification.
    
    Returns system status, index size, and model information.
    """
    try:
        response = await health_check()
        return func.HttpResponse(
            body=json.dumps(response),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Health function error: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
