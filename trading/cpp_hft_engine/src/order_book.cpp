#include "order_book.h"
#include <cstring>
#include <algorithm>

namespace magnatrix::hft {

OrderBook::OrderBook(const char* symbol) {
    std::strncpy(symbol_, symbol, 15);
    symbol_[15] = '\0';
    scratch_bids_.reserve(256);
    scratch_asks_.reserve(256);
}

void OrderBook::update_l1(PriceInt bid, QuantityInt bid_qty,
                          PriceInt ask, QuantityInt ask_qty, Timestamp ts) {
    std::lock_guard<std::mutex> lock(mutex_);

    bids_.clear();
    asks_.clear();

    if (bid > 0 && bid_qty > 0) {
        bids_[bid] = PriceLevel(bid);
        bids_[bid].total_qty = bid_qty;
        bids_[bid].order_count = 1;
    }
    if (ask > 0 && ask_qty > 0) {
        asks_[ask] = PriceLevel(ask);
        asks_[ask].total_qty = ask_qty;
        asks_[ask].order_count = 1;
    }

    last_update_ts_.store(ts, std::memory_order_relaxed);
    update_count_.fetch_add(1, std::memory_order_relaxed);
}

void OrderBook::add_bid(PriceInt price, QuantityInt qty) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = bids_.find(price);
    if (it != bids_.end()) {
        it->second.total_qty += qty;
        it->second.order_count++;
    } else {
        PriceLevel pl(price);
        pl.total_qty = qty;
        pl.order_count = 1;
        bids_[price] = pl;
    }
    update_count_.fetch_add(1, std::memory_order_relaxed);
}

void OrderBook::add_ask(PriceInt price, QuantityInt qty) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = asks_.find(price);
    if (it != asks_.end()) {
        it->second.total_qty += qty;
        it->second.order_count++;
    } else {
        PriceLevel pl(price);
        pl.total_qty = qty;
        pl.order_count = 1;
        asks_[price] = pl;
    }
    update_count_.fetch_add(1, std::memory_order_relaxed);
}

void OrderBook::remove_bid(PriceInt price, QuantityInt qty) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = bids_.find(price);
    if (it == bids_.end()) return;
    it->second.total_qty -= qty;
    if (it->second.total_qty <= 0) {
        bids_.erase(it);
    }
    update_count_.fetch_add(1, std::memory_order_relaxed);
}

void OrderBook::remove_ask(PriceInt price, QuantityInt qty) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = asks_.find(price);
    if (it == asks_.end()) return;
    it->second.total_qty -= qty;
    if (it->second.total_qty <= 0) {
        asks_.erase(it);
    }
    update_count_.fetch_add(1, std::memory_order_relaxed);
}

PriceInt OrderBook::best_bid() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (bids_.empty()) return 0;
    return bids_.begin()->first;
}

PriceInt OrderBook::best_ask() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (asks_.empty()) return 0;
    return asks_.begin()->first;
}

QuantityInt OrderBook::best_bid_qty() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (bids_.empty()) return 0;
    return bids_.begin()->second.total_qty;
}

QuantityInt OrderBook::best_ask_qty() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (asks_.empty()) return 0;
    return asks_.begin()->second.total_qty;
}

PriceInt OrderBook::spread() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (bids_.empty() || asks_.empty()) return 0;
    return asks_.begin()->first - bids_.begin()->first;
}

double OrderBook::spread_bps() const {
    PriceInt mid = mid_price();
    if (mid == 0) return 0.0;
    PriceInt sp = spread();
    return (sp * 10000.0) / mid;  // basis points
}

PriceInt OrderBook::mid_price() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (bids_.empty() || asks_.empty()) return 0;
    return (bids_.begin()->first + asks_.begin()->first) / 2;
}

std::vector<PriceLevel> OrderBook::bids_snapshot(size_t n) const {
    std::lock_guard<std::mutex> lock(mutex_);
    scratch_bids_.clear();
    size_t count = 0;
    for (const auto& [price, level] : bids_) {
        if (count >= n) break;
        scratch_bids_.push_back(level);
        count++;
    }
    return scratch_bids_;
}

std::vector<PriceLevel> OrderBook::asks_snapshot(size_t n) const {
    std::lock_guard<std::mutex> lock(mutex_);
    scratch_asks_.clear();
    size_t count = 0;
    for (const auto& [price, level] : asks_) {
        if (count >= n) break;
        scratch_asks_.push_back(level);
        count++;
    }
    return scratch_asks_;
}

PriceInt OrderBook::vwap_bid(size_t depth) const {
    std::lock_guard<std::mutex> lock(mutex_);
    QuantityInt total_qty = 0;
    __int128_t weighted_sum = 0;
    size_t count = 0;
    for (const auto& [price, level] : bids_) {
        if (count >= depth) break;
        weighted_sum += static_cast<__int128_t>(price) * level.total_qty;
        total_qty += level.total_qty;
        count++;
    }
    if (total_qty == 0) return 0;
    return static_cast<PriceInt>(weighted_sum / total_qty);
}

PriceInt OrderBook::vwap_ask(size_t depth) const {
    std::lock_guard<std::mutex> lock(mutex_);
    QuantityInt total_qty = 0;
    __int128_t weighted_sum = 0;
    size_t count = 0;
    for (const auto& [price, level] : asks_) {
        if (count >= depth) break;
        weighted_sum += static_cast<__int128_t>(price) * level.total_qty;
        total_qty += level.total_qty;
        count++;
    }
    if (total_qty == 0) return 0;
    return static_cast<PriceInt>(weighted_sum / total_qty);
}

double OrderBook::imbalance(size_t depth) const {
    std::lock_guard<std::mutex> lock(mutex_);
    QuantityInt bid_qty = 0;
    QuantityInt ask_qty = 0;
    size_t count = 0;
    for (const auto& [price, level] : bids_) {
        if (count >= depth) break;
        bid_qty += level.total_qty;
        count++;
    }
    count = 0;
    for (const auto& [price, level] : asks_) {
        if (count >= depth) break;
        ask_qty += level.total_qty;
        count++;
    }
    QuantityInt total = bid_qty + ask_qty;
    if (total == 0) return 0.0;
    return static_cast<double>(bid_qty - ask_qty) / static_cast<double>(total);
}

// ── OrderBookManager ────────────────────────────────────────────────────────

OrderBookManager::OrderBookManager() = default;

OrderBook* OrderBookManager::get_or_create(const char* symbol) {
    std::string key(symbol);
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = books_.find(key);
    if (it != books_.end()) {
        return it->second.get();
    }
    auto book = std::make_unique<OrderBook>(symbol);
    OrderBook* ptr = book.get();
    books_[key] = std::move(book);
    return ptr;
}

OrderBook* OrderBookManager::get(const char* symbol) {
    std::string key(symbol);
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = books_.find(key);
    if (it != books_.end()) return it->second.get();
    return nullptr;
}

void OrderBookManager::remove(const char* symbol) {
    std::string key(symbol);
    std::lock_guard<std::mutex> lock(mutex_);
    books_.erase(key);
}

size_t OrderBookManager::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return books_.size();
}

std::vector<std::string> OrderBookManager::symbols() const {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<std::string> result;
    result.reserve(books_.size());
    for (const auto& [sym, _] : books_) {
        result.push_back(sym);
    }
    return result;
}

} // namespace magnatrix::hft
