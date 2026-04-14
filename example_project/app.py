"""A small FastAPI app with intentional bugs for TestForge demo."""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="BookStore API", version="0.1.0")

# In-memory store
BOOKS: dict[int, dict] = {
    1: {"id": 1, "title": "Dune", "author": "Frank Herbert", "price": 12.99},
    2: {"id": 2, "title": "Neuromancer", "author": "William Gibson", "price": 9.99},
}

_next_id = 3


class BookCreate(BaseModel):
    title: str
    author: str
    price: float


class Book(BaseModel):
    id: int
    title: str
    author: str
    price: float


@app.get("/books", response_model=list[Book])
def list_books():
    return list(BOOKS.values())


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int):
    if book_id not in BOOKS:
        raise HTTPException(status_code=404, detail="Book not found")
    return BOOKS[book_id]


@app.post("/books", response_model=Book, status_code=201)
def create_book(book: BookCreate):
    global _next_id
    new_book = {"id": _next_id, "title": book.title, "author": book.author, "price": book.price}
    BOOKS[_next_id] = new_book
    _next_id += 1
    return new_book


@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    if book_id not in BOOKS:
        raise HTTPException(status_code=404, detail="Book not found")
    del BOOKS[book_id]
    return {"deleted": True}


# --- BUG 1: SQL-injection-like string concatenation (semgrep should flag) ---
@app.get("/search")
def search_books(q: str = Query(...)):
    query = "SELECT * FROM books WHERE title LIKE '%" + q + "%'"  # noqa: S608
    # In reality we just filter in-memory, but the string is suspicious
    results = [b for b in BOOKS.values() if q.lower() in b["title"].lower()]
    return {"query_debug": query, "results": results}


# --- BUG 2: Division by zero in discount calc ---
def calculate_discount(price: float, quantity: int) -> float:
    """Calculate per-unit discount. BUG: crashes when quantity is 0."""
    total = price * quantity
    return total / quantity  # ZeroDivisionError when quantity=0


# --- BUG 3: Off-by-one in pagination ---
def paginate(items: list, page: int, per_page: int = 10) -> list:
    """BUG: skips first item due to off-by-one."""
    start = page * per_page + 1  # should be page * per_page
    end = start + per_page
    return items[start:end]
