#pragma once
#include "order_book.h"
#include "arbitrage_detector.h"
#include <memory>
#include <string>
#include <atomic>

namespace magnatrix::hft {

// HFT Engine: tick-to-trade pipeline
class HFTEngine {
public:
    HFTEngine();
    ~HFTEngine() = default;

    // Initialize the engine
    bool init();

    // Shutdown
    void shutdown();

    // Process a market tick (L1 update)
    void on_tick(const Tick& tick);

    // Process a trade fill
    void on_trade(const TradeFill& fill);

    // Get order book manager
    OrderBookManager* book_manager() { return &book_manager_; }

    // Get arbitrage detector
    ArbitrageDetector* arb_detector() { return &arb_detector_; }

    // Latency metrics (nanoseconds)
    uint64_t avg_tick_latency_ns() const;
    uint64_t max_tick_latency_ns() const;
    uint64_t total_ticks_processed() const { return tick_count_.load(std::memory_order_relaxed); }

    // Engine status
    bool is_running() const { return running_.load(std::memory_order_relaxed); }

private:
    OrderBookManager book_manager_;
    ArbitrageDetector arb_detector_;
    std::atomic<bool> running_{false};
    std::atomic<uint64_t> tick_count_{0};
    std::atomic<uint64_t> latency_sum_ns_{0};
    std::atomic<uint64_t> latency_max_ns_{0};
};

} // namespace magnatrix::hft
