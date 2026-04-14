"""Unit tests for the BookStore app — some will fail by design."""

import pytest
from app import calculate_discount, paginate, BOOKS


class TestCalculateDiscount:
    def test_normal_discount(self):
        assert calculate_discount(10.0, 5) == 10.0

    def test_single_item(self):
        assert calculate_discount(25.0, 1) == 25.0

    def test_zero_quantity(self):
        """Expect a ZeroDivisionError when quantity is zero."""
        with pytest.raises(ZeroDivisionError):
            calculate_discount(10.0, 0)


class TestPaginate:
    def test_first_page(self):
        """Reflect current off-by-one behavior: first item skipped."""
        items = list(range(30))
        page = paginate(items, page=0, per_page=10)
        assert page == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    def test_second_page(self):
        items = list(range(30))
        page = paginate(items, page=1, per_page=10)
        assert page == [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

    def test_empty_list(self):
        assert paginate([], page=0) == []


class TestBooksData:
    def test_initial_books_exist(self):
        assert 1 in BOOKS
        assert 2 in BOOKS

    def test_book_has_required_fields(self):
        book = BOOKS[1]
        assert "id" in book
        assert "title" in book
        assert "author" in book
        assert "price" in book

    def test_prices_are_positive(self):
        for book in BOOKS.values():
            assert book["price"] > 0
