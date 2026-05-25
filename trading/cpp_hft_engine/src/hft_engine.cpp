#include "hft_engine.h"
#include <chrono>

namespace magnatrix::hft {

HFTEngine::HFTEngine() = default;

bool HFTEngine::init() {
    running_.store(true, std::memory_order_relaxed);
    return true;
}

void HFTEngine::shutdown() {
    running_.store(false, std::memory_order_relaxed);
}

void HFTEngine::on_tick(const Tick& tick) {
    auto t0 = std::chrono::high_resolution_clock::now();

    // Get or create order book for this symbol
    OrderBook* book = book_manager_.get_or_create(tick.symbol);
    if (book) {
        book->update_l1(tick.bid, tick.bid_qty, tick.ask, tick.ask_qty, tick.ts);
    }

    auto t1 = std::chrono::high_resolution_clock::now();
    uint64_t latency = std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count();

    latency_sum_ns_.fetch_add(latency, std::memory_order_relaxed);
    tick_count_.fetch_add(1, std::memory_order_relaxed);

    uint64_t current_max = latency_max_ns_.load(std::memory_order_relaxed);
    while (latency > current_max) {
        if (latency_max_ns_.compare_exchange_weak(current_max, latency,
                                                  std::memory_order_relaxed,
                                                  std::memory_order_relaxed)) {
            break;
        }
    }
}

void HFTEngine::on_trade(const TradeFill& fill) {
    // Update book with trade fill (reduce liquidity)
    OrderBook* book = book_manager_.get(fill.symbol);
    if (!book) return;

    if (fill.side == Side::BUY) {
        // Taker bought at ask -> reduce ask liquidity
        book->remove_ask(fill.price, fill.quantity);
    } else {
        // Taker sold at bid -> reduce bid liquidity
        book->remove_bid(fill.price, fill.quantity);
    }
}

uint64_t HFTEngine::avg_tick_latency_ns() const {
    uint64_t count = tick_count_.load(std::memory_order_relaxed);
    if (count == 0) return 0;
    return latency_sum_ns_.load(std::memory_order_relaxed) / count;
}

uint64_t HFTEngine::max_tick_latency_ns() const {
    return latency_max_ns_.load(std::memory_order_relaxed);
}

} // namespace magnatrix::hft
