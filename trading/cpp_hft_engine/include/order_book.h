#pragma once
#include "market_data.h"
#include <map>
#include <vector>
#include <memory>
#include <mutex>
#include <atomic>

namespace magnatrix::hft {

// Price level in the order book
struct PriceLevel {
    PriceInt price;
    QuantityInt total_qty;
    uint32_t order_count;

    PriceLevel(PriceInt p = 0) : price(p), total_qty(0), order_count(0) {}
};

// Lock-free aligned price level for cache-line optimization
struct alignas(64) AlignedPriceLevel {
    std::atomic<PriceInt> price{0};
    std::atomic<QuantityInt> total_qty{0};
    std::atomic<uint32_t> order_count{0};
};

// Limit Order Book (LOB) — sorted bid/ask levels
class OrderBook {
public:
    explicit OrderBook(const char* symbol);
    ~OrderBook() = default;

    // Non-copyable, non-movable (mutex member)
    OrderBook(const OrderBook&) = delete;
    OrderBook& operator=(const OrderBook&) = delete;
    OrderBook(OrderBook&&) = delete;
    OrderBook& operator=(OrderBook&&) = delete;

    // Update from tick
    void update_l1(PriceInt bid, QuantityInt bid_qty, PriceInt ask, QuantityInt ask_qty, Timestamp ts);

    // Add/remove liquidity at a price level
    void add_bid(PriceInt price, QuantityInt qty);
    void add_ask(PriceInt price, QuantityInt qty);
    void remove_bid(PriceInt price, QuantityInt qty);
    void remove_ask(PriceInt price, QuantityInt qty);

    // Get best bid/ask
    PriceInt best_bid() const;
    PriceInt best_ask() const;
    QuantityInt best_bid_qty() const;
    QuantityInt best_ask_qty() const;

    // Get spread in fixed-point
    PriceInt spread() const;
    double spread_bps() const;  // spread in basis points

    // Get top N levels (snapshot)
    std::vector<PriceLevel> bids_snapshot(size_t n = 10) const;
    std::vector<PriceLevel> asks_snapshot(size_t n = 10) const;

    // Mid price
    PriceInt mid_price() const;

    // VWAP of top N levels
    PriceInt vwap_bid(size_t depth = 5) const;
    PriceInt vwap_ask(size_t depth = 5) const;

    // Book imbalance: (bid_qty - ask_qty) / (bid_qty + ask_qty)
    double imbalance(size_t depth = 5) const;

    // Stats
    uint64_t update_count() const { return update_count_.load(std::memory_order_relaxed); }
    Timestamp last_update_ts() const { return last_update_ts_.load(std::memory_order_relaxed); }

    const char* symbol() const { return symbol_; }

private:
    char symbol_[16];

    // Bids: descending price (highest first)
    std::map<PriceInt, PriceLevel, std::greater<PriceInt>> bids_;
    // Asks: ascending price (lowest first)
    std::map<PriceInt, PriceLevel, std::less<PriceInt>> asks_;

    mutable std::mutex mutex_;

    std::atomic<uint64_t> update_count_{0};
    std::atomic<Timestamp> last_update_ts_{0};

    // Pre-allocated scratch space for snapshots
    mutable std::vector<PriceLevel> scratch_bids_;
    mutable std::vector<PriceLevel> scratch_asks_;
};

// Multi-symbol order book manager
class OrderBookManager {
public:
    OrderBookManager();
    ~OrderBookManager() = default;

    OrderBook* get_or_create(const char* symbol);
    OrderBook* get(const char* symbol);
    void remove(const char* symbol);
    size_t size() const;
    std::vector<std::string> symbols() const;

private:
    std::unordered_map<std::string, std::unique_ptr<OrderBook>> books_;
    mutable std::mutex mutex_;
};

} // namespace magnatrix::hft
