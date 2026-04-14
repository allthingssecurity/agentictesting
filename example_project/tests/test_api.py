"""Integration tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


class TestListBooks:
    def test_list_returns_books(self):
        resp = client.get("/books")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    def test_list_book_structure(self):
        resp = client.get("/books")
        book = resp.json()[0]
        assert "id" in book
        assert "title" in book


class TestGetBook:
    def test_get_existing(self):
        resp = client.get("/books/1")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Dune"

    def test_get_nonexistent(self):
        resp = client.get("/books/999")
        assert resp.status_code == 404


class TestCreateBook:
    def test_create_valid(self):
        resp = client.post("/books", json={"title": "Snow Crash", "author": "Neal Stephenson", "price": 11.99})
        assert resp.status_code == 201
        assert resp.json()["title"] == "Snow Crash"

    def test_create_missing_field(self):
        resp = client.post("/books", json={"title": "Incomplete"})
        assert resp.status_code == 422


class TestSearch:
    def test_search_finds_book(self):
        resp = client.get("/search?q=dune")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) >= 1

    def test_search_returns_debug_query(self):
        """This exposes the SQL-injection-like debug string."""
        resp = client.get("/search?q=test")
        data = resp.json()
        assert "query_debug" in data
