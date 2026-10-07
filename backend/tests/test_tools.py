"""Tool results must match the database exactly. Run from backend/: python -m pytest tests -q"""

import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import InvalidSize, PriceInfo, ProductDescription, ProductNotFound, StockReport  # noqa: E402
from tools import DB_PATH, AgentDeps, check_stock, get_price, get_product_description, search_products  # noqa: E402


@pytest.fixture
def ctx():
    return SimpleNamespace(deps=AgentDeps())


def db(sql, *args):
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


ALL_IDS = [r[0] for r in db("SELECT product_id FROM catalogue")]
SOLD_OUT = db("SELECT product_id, size FROM inventory WHERE quantity = 0 LIMIT 5")


@pytest.mark.parametrize("pid", ALL_IDS)
def test_price_matches_db_for_every_product(ctx, pid):
    (price,), = db("SELECT price FROM catalogue WHERE product_id = ?", pid)
    result = get_price(ctx, pid)
    assert isinstance(result, PriceInfo)
    assert result.price == price
    assert result.price_display == f"${price:,.2f}"
    assert round(price, 2) in ctx.deps.seen_prices


def test_description_matches_db(ctx):
    pid = "basic-hoodie-big-yale"
    (desc,), = db("SELECT description FROM catalogue WHERE product_id = ?", pid)
    result = get_product_description(ctx, pid)
    assert isinstance(result, ProductDescription)
    assert result.description == desc
    assert "navy blue" in result.colors


def test_lookup_by_exact_name(ctx):
    assert get_price(ctx, "Basic Hoodie Big Yale").product_id == "basic-hoodie-big-yale"


@pytest.mark.parametrize("pid,size", SOLD_OUT)
def test_sold_out_size_is_reported(ctx, pid, size):
    result = check_stock(ctx, pid, size)
    assert isinstance(result, StockReport)
    assert result.requested_size_status == "sold_out"
    assert result.sizes[0].quantity == 0
    assert size in result.sold_out_sizes and size not in result.available_sizes


def test_all_sizes_match_db(ctx):
    pid = "basic-hoodie-big-yale"
    expected = dict(db("SELECT size, quantity FROM inventory WHERE product_id = ?", pid))
    result = check_stock(ctx, pid)
    assert {s.size: s.quantity for s in result.sizes} == expected
    assert [s.size for s in result.sizes] == ["XS", "S", "M", "L", "XL", "XXL"]
    assert result.total_quantity == sum(expected.values())


@pytest.mark.parametrize("spoken,canonical", [("medium", "M"), ("2XL", "XXL"), ("extra large", "XL"), ("s", "S")])
def test_size_words_are_normalized(ctx, spoken, canonical):
    assert check_stock(ctx, "basic-hoodie-big-yale", spoken).requested_size == canonical


def test_low_stock_status(ctx):
    pid, size, qty = db("SELECT product_id, size, quantity FROM inventory WHERE quantity BETWEEN 1 AND 3 LIMIT 1")[0]
    assert check_stock(ctx, pid, size).requested_size_status == "low_stock"


def test_invalid_size(ctx):
    result = check_stock(ctx, "basic-hoodie-big-yale", "XXXL")
    assert isinstance(result, InvalidSize)
    assert result.valid_sizes == ["XS", "S", "M", "L", "XL", "XXL"]


def test_unknown_product_returns_suggestions_not_a_guess(ctx):
    result = get_price(ctx, "berkeley hoodie thing")
    assert isinstance(result, ProductNotFound)
    assert result.suggestions
    assert not ctx.deps.seen_prices


def test_search_filters_and_prices(ctx):
    found = search_products(ctx, "", garment_type="t-shirt", max_price=35)
    assert found.results
    for r in found.results:
        (price,), = db("SELECT price FROM catalogue WHERE product_id = ?", r.product_id)
        assert r.price == price <= 35
        assert r.product_id in ctx.deps.seen_product_ids


@pytest.mark.parametrize("typo,fixed,expect_in_name", [
    ("crewnek", "crewneck", "Crewneck"),
    ("brnaford", "branford", "Branford"),
    ("berkly", "berkeley", "Berkeley"),
    ("lacrose", "lacrosse", "Lacrosse"),
    ("saybrok", "saybrook", "Saybrook"),
])
def test_fuzzy_search_corrects_typos(ctx, typo, fixed, expect_in_name):
    found = search_products(ctx, typo)
    assert found.corrections == {typo: fixed}
    assert expect_in_name in found.results[0].name


def test_fuzzy_corrects_filters(ctx):
    found = search_products(ctx, "", garment_type="hoody", color="nvy")
    assert found.corrections == {"hoody": "hood", "nvy": "navy"}
    assert found.results and all("navy" in " ".join(r.colors) for r in found.results)


def test_correct_words_are_not_changed(ctx):
    assert search_products(ctx, "navy hoodie").corrections == {}


def test_gibberish_finds_nothing(ctx):
    found = search_products(ctx, "xyzzy")
    assert found.total_matches == 0 and found.corrections == {}
