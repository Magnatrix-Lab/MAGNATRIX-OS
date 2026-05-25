#pragma once
#include "market_data.h"
#include "order_book.h"
#include <vector>
#include <string>
#include <mutex>
#include <atomic>
#include <chrono>

namespace magnatrix::hft {

// Arbitrage opportunity detected between two exchanges
struct ArbitrageOpportunity {
    char symbol[16];
    uint8_t buy_exchange;   // exchange to buy on
    uint8_t sell_exchange;  // exchange to sell on
    PriceInt buy_price;     // price to buy at
    PriceInt sell_price;    // price to sell at
    double profit_bps;      // profit in basis points after estimated fees
    Timestamp detected_at;
    double estimated_fees_bps;  // estimated round-trip fees

    ArbitrageOpportunity() : buy_exchange(0), sell_exchange(0), buy_price(0),
        sell_price(0), profit_bps(0.0), detected_at(0), estimated_fees_bps(0.0) {
        std::memset(symbol, 0, sizeof(symbol));
    }
};

// Fee schedule per exchange (in basis points)
struct FeeSchedule {
    double maker_bps;
    double taker_bps;
    double withdrawal_bps;

    FeeSchedule(double m = 2.0, double t = 5.0, double w = 0.0)
        : maker_bps(m), taker_bps(t), withdrawal_bps(w) {}
};

// Cross-exchange arbitrage detector
class ArbitrageDetector {
public:
    ArbitrageDetector();
    ~ArbitrageDetector() = default;

    // Register an order book for an exchange
    void register_book(uint8_t exchange_id, const char* symbol, OrderBook* book);
    void unregister_book(uint8_t exchange_id, const char* symbol);

    // Set fee schedule for an exchange
    void set_fee_schedule(uint8_t exchange_id, const FeeSchedule& fees);

    // Minimum profit threshold in bps to report
    void set_min_profit_bps(double bps) { min_profit_bps_ = bps; }

    // Scan all registered pairs for arbitrage
    std::vector<ArbitrageOpportunity> scan();

    // Scan a specific symbol
    std::vector<ArbitrageOpportunity> scan_symbol(const char* symbol);

    // Stats
    uint64_t scans_count() const { return scans_count_.load(std::memory_order_relaxed); }
    uint64_t opportunities_found() const { return opp_count_.load(std::memory_order_relaxed); }

private:
    // Key: "symbol:exchange_id"
    std::unordered_map<std::string, OrderBook*> books_;
    std::unordered_map<uint8_t, FeeSchedule> fees_;
    mutable std::mutex mutex_;

    double min_profit_bps_ = 5.0;  // default 5 bps minimum
    std::atomic<uint64_t> scans_count_{0};
    std::atomic<uint64_t> opp_count_{0};

    std::string make_key(const char* symbol, uint8_t exchange_id) const;
};

} // namespace magnatrix::hft
