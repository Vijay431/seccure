"""Thin GitHub REST API client with automatic retry/backoff."""

from __future__ import annotations

import os

import httpx

_BASE = "https://api.github.com"
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _client() -> httpx.Client:
    token = os.environ["GITHUB_TOKEN"]
    transport = httpx.HTTPTransport(retries=3)
    return httpx.Client(
        base_url=_BASE,
        headers={**_HEADERS, "Authorization": f"Bearer {token}"},
        transport=transport,
        timeout=30,
    )


def get(path: str, **params: str | int) -> dict | list:
    """Perform a GET request and return the parsed JSON body."""
    with _client() as client:
        resp = client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()


def post(path: str, body: dict) -> dict:
    """Perform a POST request and return the parsed JSON body."""
    with _client() as client:
        resp = client.post(path, json=body)
        resp.raise_for_status()
        return resp.json()


def patch(path: str, body: dict) -> dict:
    """Perform a PATCH request and return the parsed JSON body."""
    with _client() as client:
        resp = client.patch(path, json=body)
        resp.raise_for_status()
        return resp.json()
