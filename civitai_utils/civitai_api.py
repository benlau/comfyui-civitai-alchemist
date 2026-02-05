"""
Civitai API Wrapper

Provides methods for interacting with the Civitai REST API.

API Documentation: https://github.com/civitai/civitai/wiki/REST-API-Reference
"""

import json
import logging
import time
import traceback
import requests
from typing import Dict, List, Optional

logger = logging.getLogger("civitai_alchemist.api")


class CivitaiAPI:
    """
    Civitai API client with retry logic and error handling.
    """

    BASE_URL = "https://civitai.com/api/v1"

    def __init__(self, api_key: Optional[str] = None,
                 api_log: Optional[list] = None):
        """
        Initialize Civitai API client.

        Args:
            api_key: Civitai API key (optional, required for some endpoints)
            api_log: Optional list to record raw API call details (for debug mode)
        """
        self.api_key = api_key
        self.api_log = api_log
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make an HTTP request with retry logic.

        Retries up to 3 times with exponential backoff (1s, 2s, 4s).
        Handles 429 rate limiting by respecting Retry-After header.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                start = time.monotonic()
                response = self.session.request(method, url, timeout=30, **kwargs)
                elapsed_ms = round((time.monotonic() - start) * 1000)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    print(f"  Rate limited, waiting {retry_after}s...")
                    logger.warning("Rate limited, waiting %ds...", retry_after)
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()

                # Record to api_log if enabled (debug mode)
                if self.api_log is not None:
                    try:
                        body = response.json()
                    except Exception:
                        body = "(non-JSON response)"
                    self.api_log.append({
                        "method": method,
                        "url": str(response.url),
                        "status_code": response.status_code,
                        "elapsed_ms": elapsed_ms,
                        "response_size_bytes": len(response.content),
                        "response_body": body,
                    })
                    logger.debug("API %s %s -> %d (%dms)",
                                 method, url, response.status_code, elapsed_ms)

                return response

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"  Request failed ({e}), retrying in {wait}s...")
                    logger.warning("Request failed (%s), retrying in %ds...", e, wait)
                    time.sleep(wait)
                else:
                    # Record failed request to api_log
                    if self.api_log is not None:
                        self.api_log.append({
                            "method": method,
                            "url": url,
                            "status_code": None,
                            "error": str(e),
                            "traceback": traceback.format_exc(),
                        })
                    raise

    def get_image_metadata(self, image_id: int) -> Optional[Dict]:
        """
        Get image metadata from Civitai.

        Args:
            image_id: Image ID

        Returns:
            Image data dictionary, or None if not found
        """
        url = f"{self.BASE_URL}/images"
        params = {"imageId": image_id, "nsfw": "X"}

        try:
            response = self._request("GET", url, params=params)
            data = response.json()
            items = data.get("items", [])
            if items:
                return items[0]
            return None
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def get_model_version_by_hash(self, file_hash: str) -> Optional[Dict]:
        """
        Look up a model version by file hash.

        Args:
            file_hash: SHA256 hash (or partial hash) of the model file

        Returns:
            Model version data dictionary, or None if not found
        """
        url = f"{self.BASE_URL}/model-versions/by-hash/{file_hash}"

        try:
            response = self._request("GET", url)
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def get_model_version(self, version_id: int) -> Optional[Dict]:
        """
        Get model version details by version ID.

        Args:
            version_id: Model version ID

        Returns:
            Model version data dictionary, or None if not found
        """
        url = f"{self.BASE_URL}/model-versions/{version_id}"

        try:
            response = self._request("GET", url)
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def search_models(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search for models by name.

        Args:
            query: Search query
            limit: Max results to return

        Returns:
            List of model data dictionaries
        """
        url = f"{self.BASE_URL}/models"
        params = {"query": query, "limit": limit}

        response = self._request("GET", url, params=params)
        data = response.json()
        return data.get("items", [])

    def get_image_generation_data(self, image_id: int) -> Optional[Dict]:
        """
        Get server-side resolved generation data from Civitai's tRPC endpoint.

        This returns resources with modelVersionId even when the uploader
        has hidden model info from the embedded metadata.

        Args:
            image_id: Image ID

        Returns:
            Generation data dict with 'meta' and 'resources' keys, or None
        """
        url = "https://civitai.com/api/trpc/image.getGenerationData"
        params = {"input": json.dumps({"json": {"id": image_id}})}

        try:
            response = self._request("GET", url, params=params)
            data = response.json()
            return data.get("result", {}).get("data", {}).get("json")
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def get_model(self, model_id: int) -> Optional[Dict]:
        """
        Get model details by ID.

        Args:
            model_id: Model ID

        Returns:
            Model data dictionary, or None if not found
        """
        url = f"{self.BASE_URL}/models/{model_id}"

        try:
            response = self._request("GET", url)
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise
