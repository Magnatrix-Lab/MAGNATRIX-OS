#include "order_book.h"
#include <iostream>
#include <cassert>
#include <cmath>

using namespace magnatrix::hft;

int main() {
    int passed = 0;
    int failed = 0;

    auto check = [&](const char* name, bool condition) {
        if (condition) { passed++; std::cout << "PASS: " << name << "\n"; }
        else { failed++; std::cout << "FAIL: " << name << "\n"; }
    };

    // Test 1: Create order book
    OrderBook book("BTCUSDT");
    check("create_book", std::strcmp(book.symbol(), "BTCUSDT") == 0);

    // Test 2: Update L1
    book.update_l1(price_to_fixed(50000.0), qty_to_fixed(1.5),
                   price_to_fixed(50001.0), qty_to_fixed(2.0), 1234567890);
    check("best_bid", fixed_to_price(book.best_bid()) == 50000.0);
    check("best_ask", fixed_to_price(book.best_ask()) == 50001.0);
    check("spread", fixed_to_price(book.spread()) == 1.0);

    // Test 3: Add liquidity
    book.add_bid(price_to_fixed(49999.0), qty_to_fixed(0.5));
    book.add_ask(price_to_fixed(50002.0), qty_to_fixed(1.0));
    auto bids = book.bids_snapshot(5);
    check("bid_snapshot_count", bids.size() == 2);

    // Test 4: Mid price
    check("mid_price", fixed_to_price(book.mid_price()) == 50000.5);

    // Test 5: VWAP
    check("vwap_bid", fixed_to_price(book.vwap_bid(5)) > 0);
    check("vwap_ask", fixed_to_price(book.vwap_ask(5)) > 0);

    // Test 6: Imbalance
    double imb = book.imbalance(5);
    check("imbalance_range", imb >= -1.0 && imb <= 1.0);

    // Test 7: Remove liquidity
    book.remove_bid(price_to_fixed(49999.0), qty_to_fixed(0.5));
    bids = book.bids_snapshot(5);
    check("remove_bid", bids.size() == 1);

    // Test 8: Fixed-point conversions
    check("price_roundtrip", std::abs(fixed_to_price(price_to_fixed(12345.6789)) - 12345.6789) < 1e-5);

    // Test 9: OrderBookManager
    OrderBookManager mgr;
    auto* b1 = mgr.get_or_create("ETHUSDT");
    auto* b2 = mgr.get("ETHUSDT");
    check("manager_get", b1 == b2);
    check("manager_size", mgr.size() == 1);

    std::cout << "\n=== Results: " << passed << " passed, " << failed << " failed ===\n";
    return failed > 0 ? 1 : 0;
}
