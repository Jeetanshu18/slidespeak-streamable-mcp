import os
import time
import asyncio
import logging
from helper.config import SLIDESPEAK_API_KEY
from typing import Any, Optional, Literal, List, Dict
import httpx

# API Configuration
API_BASE = "https://api.slidespeak.co/api/v1"
USER_AGENT = "slidespeak-mcp/0.0.3"

# Default Timeouts
DEFAULT_TIMEOUT = 30.0
GENERATION_TIMEOUT = 90.0  # Total time allowed for generation + polling
POLLING_INTERVAL = 2.0  # Seconds between status checks
POLLING_TIMEOUT = 10.0  # Timeout for each individual status check request

async def _make_api_request(
    method: Literal["GET", "POST"],
    endpoint: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Optional[Dict[str, Any]]:
    """
    Makes an HTTP request to the SlideSpeak API.

    Args:
        method: HTTP method ('GET' or 'POST').
        endpoint: API endpoint path (e.g., '/presentation/templates').
        payload: JSON payload for POST requests. Ignored for GET.
        timeout: Request timeout in seconds.

    Returns:
        The parsed JSON response as a dictionary on success, None on failure.
    """
    api_key = SLIDESPEAK_API_KEY

    if not api_key:
        logging.error("API Key is missing. Cannot make API request.")
        return None

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "X-API-Key": api_key,
    }

    # Construct full URL
    url = f"{API_BASE}{endpoint}"

    async with httpx.AsyncClient() as client:
        try:
            if method == "POST":
                response = await client.post(url, json=payload, headers=headers, timeout=timeout)
            else:  # Default to GET
                response = await client.get(url, headers=headers, timeout=timeout)

            response.raise_for_status()  # Raise exception for 4xx or 5xx status codes
            return response.json()

        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error calling {method} {url}: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logging.error(f"Request error calling {method} {url}: {str(e)}")
        except Exception as e:
            logging.error(f"An unexpected error occurred calling {method} {url}: {str(e)}")

        return None

async def get_available_templates(limit: Optional[int] = None) -> Dict[str, Any]:
    """Get all available presentation templates with optional limit."""
    templates_endpoint = "/presentation/templates"

    templates_data = await _make_api_request("GET", templates_endpoint)

    if not templates_data:
        return {"message": "Unable to fetch templates due to an API error. Check server logs.", "is_error": True}

    if not isinstance(templates_data, list):
        return {"message": f"Unexpected response format received for templates: {type(templates_data).__name__}", "is_error": True}

    if not templates_data:
        return {"message": "No templates available.", "is_error": False}

    # Store total count before applying limit
    total_available = len(templates_data)
    
    # Apply limit if specified
    if limit is not None and limit > 0:
        templates_data = templates_data[:limit]

    formatted_templates = "Available templates:\n"
    for template in templates_data:
        # Add more robust checking for expected keys
        name = template.get("name", "default")
        images = template.get("images", {})
        cover = images.get("cover", "No cover image URL")
        content = images.get("content", "No content image URL")
        formatted_templates += f"- {name}\n  Cover: {cover}\n  Content: {content}\n\n"

    # Add limit info to the message if limit was applied
    if limit is not None and limit > 0 and total_available > limit:
        formatted_templates += f"\n(Showing {len(templates_data)} of {total_available} templates, limited by input parameter)"

    return {"message": formatted_templates.strip(), "is_error": False}

async def generate_powerpoint(plain_text: str, length: int, template: str) -> Dict[str, Any]:
    """
    Generate a PowerPoint presentation based on text, length, and template.
    Waits up to a configured time for the result.
    """
    generation_endpoint = "/presentation/generate"
    status_endpoint_base = "/task_status"  # Base path for status checks

    # Prepare the JSON body for the generation request
    payload = {
        "plain_text": plain_text,
        "length": length,
        "template": template
    }

    # Step 1: Initiate generation (POST request)
    init_result = await _make_api_request("POST", generation_endpoint, payload=payload, timeout=GENERATION_TIMEOUT)

    if not init_result:
        return {"message": "Failed to initiate PowerPoint generation due to an API error. Check server logs.", "is_error": True}

    task_id = init_result.get("task_id")
    if not task_id:
        return {"message": f"Failed to initiate PowerPoint generation. API response did not contain a task ID. Response: {init_result}", "is_error": True}

    logging.info(f"PowerPoint generation initiated. Task ID: {task_id}")

    # Step 2: Poll for the task status
    status_endpoint = f"{status_endpoint_base}/{task_id}"
    final_result = None

    while True:
        logging.debug(f"Polling status for task {task_id}...")
        status_result = await _make_api_request("GET", status_endpoint, timeout=POLLING_TIMEOUT)
        logging.info(status_result)

        if status_result:
            task_status = status_result.get("task_status")
            task_result = status_result.get("task_result")  # Assuming result might be here

            if task_status == "SUCCESS":
                logging.info(f"Task {task_id} completed successfully.")
                # Prefer task_result if available, otherwise return the whole status dict as string
                final_result = str(task_result) if task_result else str(status_result)
                final_result = f"Make sure to return the pptx url to the user if available. Here is the result: {final_result}"
                break
            elif task_status in ["FAILED", "FAILURE"]:  # Use 'FAILED' consistently if possible in API
                logging.error(f"Task {task_id} failed. Status response: {status_result}")
                error_message = task_result.get("error", "Unknown error") if isinstance(task_result, dict) else "Unknown error"
                final_result = f"PowerPoint generation failed for task {task_id}. Reason: {error_message}"
                break
            elif task_status in ["PENDING", "PROCESSING"]:  # Add other intermediate states if known
                logging.debug(f"Task {task_id} status: {task_status}. Waiting...")
            else:
                logging.warning(f"Task {task_id} has unknown status: {task_status}. Response: {status_result}")
                # Continue polling, but log this unexpected state

        else:
            # Failure during polling
            logging.warning(f"Failed to get status for task {task_id} during polling. Will retry.")
            # Optionally add a counter to break after several consecutive polling failures

        await asyncio.sleep(POLLING_INTERVAL)  # Use asyncio.sleep in async functions

    # After loop: check if we got a result or timed out
    if final_result:
        return {"message": final_result, "is_error": False}
    else:
        logging.warning(f"Timeout ({GENERATION_TIMEOUT}s) while waiting for PowerPoint generation task {task_id}.")
        return {"message": f"Timeout while waiting for PowerPoint generation (Task ID: {task_id}). The task might still be running.", "is_error": True}

async def generate_powerpoint_slide_by_slide(slides: List[Dict[str, Any]], template: str) -> Dict[str, Any]:
    """
    Generate a PowerPoint presentation slide by slide based on slides array and template.
    Waits up to a configured time for the result.
    """
    generation_endpoint = "/presentation/generate/slide-by-slide"
    status_endpoint_base = "/task_status"  # Base path for status checks

    # Prepare the JSON body for the generation request
    payload = {
        "slides": slides,
        "template": template
    }

    # Step 1: Initiate generation (POST request)
    init_result = await _make_api_request("POST", generation_endpoint, payload=payload, timeout=GENERATION_TIMEOUT)
    if not init_result:
        return {"message": "Failed to initiate PowerPoint generation due to an API error. Check server logs.", "is_error": True}

    task_id = init_result.get("task_id")
    if not task_id:
        return {"message": f"Failed to initiate PowerPoint generation. API response did not contain a task ID. Response: {init_result}", "is_error": True}

    logging.info(f"PowerPoint generation initiated. Task ID: {task_id}")

    # Step 2: Poll for the task status
    status_endpoint = f"{status_endpoint_base}/{task_id}"
    final_result = None

    while True:
        logging.debug(f"Polling status for task {task_id}...")
        status_result = await _make_api_request("GET", status_endpoint, timeout=POLLING_TIMEOUT)

        if status_result:
            task_status = status_result.get("task_status")
            task_result = status_result.get("task_result")  # Assuming result might be here

            if task_status == "SUCCESS":
                logging.info(f"Task {task_id} completed successfully.")
                # Prefer task_result if available, otherwise return the whole status dict as string
                final_result = str(task_result) if task_result else str(status_result)
                final_result = f"Make sure to return the pptx url to the user if available. Here is the result: {final_result}"
                break
            elif task_status in ["FAILED", "FAILURE"] :  # Use 'FAILED' consistently if possible in API
                logging.error(f"Task {task_id} failed. Status response: {status_result}")
                error_message = task_result.get("error", "Unknown error") if isinstance(task_result, dict) else "Unknown error"
                final_result = f"PowerPoint generation failed for task {task_id}. Reason: {error_message}"
                break
            elif task_status in ["PENDING", "PROCESSING"]:  # Add other intermediate states if known
                logging.debug(f"Task {task_id} status: {task_status}. Waiting...")
            else:
                logging.warning(f"Task {task_id} has unknown status: {task_status}. Response: {status_result}")
                # Continue polling, but log this unexpected state

        else:
            # Failure during polling
            logging.warning(f"Failed to get status for task {task_id} during polling. Will retry.")
            # Optionally add a counter to break after several consecutive polling failures

        await asyncio.sleep(POLLING_INTERVAL)  # Use asyncio.sleep in async functions

    # After loop: check if we got a result or timed out
    if final_result:
        return {"message": final_result, "is_error": False}
    else:
        logging.warning(f"Timeout ({GENERATION_TIMEOUT}s) while waiting for PowerPoint generation task {task_id}.")
        return {"message": f"Timeout while waiting for PowerPoint generation (Task ID: {task_id}). The task might still be running.", "is_error": True}