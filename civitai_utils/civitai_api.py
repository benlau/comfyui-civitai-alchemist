"""
Civitai API Wrapper

Provides methods for interacting with the Civitai REST API.

API Documentation: https://github.com/civitai/civitai/wiki/REST-API-Reference
"""

import time
import requests
from typing import Dict, List, Optional


class CivitaiAPI:
    """
    Civitai API client with retry logic and error handling.
    """

    BASE_URL = "https://civitai.com/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Civitai API client.

        Args:
            api_key: Civitai API key (optional, required for some endpoints)
        """
        self.api_key = api_key
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
                response = self.session.request(method, url, timeout=30, **kwargs)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    print(f"  Rate limited, waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"  Request failed ({e}), retrying in {wait}s...")
                    time.sleep(wait)
                else:
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
