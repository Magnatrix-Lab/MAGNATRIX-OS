#include "arbitrage_detector.h"
#include <sstream>
#include <iomanip>
#include <algorithm>

namespace magnatrix::hft {

ArbitrageDetector::ArbitrageDetector() = default;

std::string ArbitrageDetector::make_key(const char* symbol, uint8_t exchange_id) const {
    std::ostringstream oss;
    oss << symbol << ":" << static_cast<int>(exchange_id);
    return oss.str();
}

void ArbitrageDetector::register_book(uint8_t exchange_id, const char* symbol, OrderBook* book) {
    std::lock_guard<std::mutex> lock(mutex_);
    books_[make_key(symbol, exchange_id)] = book;
}

void ArbitrageDetector::unregister_book(uint8_t exchange_id, const char* symbol) {
    std::lock_guard<std::mutex> lock(mutex_);
    books_.erase(make_key(symbol, exchange_id));
}

void ArbitrageDetector::set_fee_schedule(uint8_t exchange_id, const FeeSchedule& fees) {
    std::lock_guard<std::mutex> lock(mutex_);
    fees_[exchange_id] = fees;
}

std::vector<ArbitrageOpportunity> ArbitrageDetector::scan() {
    std::lock_guard<std::mutex> lock(mutex_);
    scans_count_.fetch_add(1, std::memory_order_relaxed);

    std::vector<ArbitrageOpportunity> results;

    // Group books by symbol
    std::unordered_map<std::string, std::vector<std::pair<uint8_t, OrderBook*>>> by_symbol;
    for (const auto& [key, book] : books_) {
        size_t pos = key.find_last_of(':');
        if (pos == std::string::npos) continue;
        std::string symbol = key.substr(0, pos);
        uint8_t ex_id = static_cast<uint8_t>(std::stoi(key.substr(pos + 1)));
        by_symbol[symbol].push_back({ex_id, book});
    }

    for (const auto& [symbol, ex_books] : by_symbol) {
        if (ex_books.size() < 2) continue;

        for (size_t i = 0; i < ex_books.size(); ++i) {
            for (size_t j = i + 1; j < ex_books.size(); ++j) {
                auto [buy_ex, buy_book] = ex_books[i];
                auto [sell_ex, sell_book] = ex_books[j];

                PriceInt buy_price = buy_book->best_ask();
                PriceInt sell_price = sell_book->best_bid();

                if (buy_price <= 0 || sell_price <= 0) continue;
                if (sell_price <= buy_price) continue;

                // Get fees
                double buy_taker_bps = 5.0;
                double sell_taker_bps = 5.0;
                auto fit = fees_.find(buy_ex);
                if (fit != fees_.end()) buy_taker_bps = fit->second.taker_bps;
                auto fit2 = fees_.find(sell_ex);
                if (fit2 != fees_.end()) sell_taker_bps = fit2->second.taker_bps;

                double total_fees_bps = buy_taker_bps + sell_taker_bps;
                double gross_profit_bps = ((sell_price - buy_price) * 10000.0) / buy_price;
                double net_profit_bps = gross_profit_bps - total_fees_bps;

                if (net_profit_bps >= min_profit_bps_) {
                    ArbitrageOpportunity opp;
                    std::strncpy(opp.symbol, symbol.c_str(), 15);
                    opp.symbol[15] = '\0';
                    opp.buy_exchange = buy_ex;
                    opp.sell_exchange = sell_ex;
                    opp.buy_price = buy_price;
                    opp.sell_price = sell_price;
                    opp.profit_bps = net_profit_bps;
                    opp.estimated_fees_bps = total_fees_bps;
                    opp.detected_at = std::chrono::duration_cast<std::chrono::nanoseconds>(
                        std::chrono::high_resolution_clock::now().time_since_epoch()).count();
                    results.push_back(opp);
                    opp_count_.fetch_add(1, std::memory_order_relaxed);
                }

                // Check reverse direction
                PriceInt buy_price2 = sell_book->best_ask();
                PriceInt sell_price2 = buy_book->best_bid();
                if (buy_price2 > 0 && sell_price2 > 0 && sell_price2 > buy_price2) {
                    double buy_taker_bps2 = 5.0;
                    double sell_taker_bps2 = 5.0;
                    auto fit3 = fees_.find(sell_ex);
                    if (fit3 != fees_.end()) buy_taker_bps2 = fit3->second.taker_bps;
                    auto fit4 = fees_.find(buy_ex);
                    if (fit4 != fees_.end()) sell_taker_bps2 = fit4->second.taker_bps;

                    double total_fees_bps2 = buy_taker_bps2 + sell_taker_bps2;
                    double gross_profit_bps2 = ((sell_price2 - buy_price2) * 10000.0) / buy_price2;
                    double net_profit_bps2 = gross_profit_bps2 - total_fees_bps2;

                    if (net_profit_bps2 >= min_profit_bps_) {
                        ArbitrageOpportunity opp;
                        std::strncpy(opp.symbol, symbol.c_str(), 15);
                        opp.symbol[15] = '\0';
                        opp.buy_exchange = sell_ex;
                        opp.sell_exchange = buy_ex;
                        opp.buy_price = buy_price2;
                        opp.sell_price = sell_price2;
                        opp.profit_bps = net_profit_bps2;
                        opp.estimated_fees_bps = total_fees_bps2;
                        opp.detected_at = std::chrono::duration_cast<std::chrono::nanoseconds>(
                            std::chrono::high_resolution_clock::now().time_since_epoch()).count();
                        results.push_back(opp);
                        opp_count_.fetch_add(1, std::memory_order_relaxed);
                    }
                }
            }
        }
    }

    // Sort by profit descending
    std::sort(results.begin(), results.end(),
        [](const ArbitrageOpportunity& a, const ArbitrageOpportunity& b) {
            return a.profit_bps > b.profit_bps;
        });

    return results;
}

std::vector<ArbitrageOpportunity> ArbitrageDetector::scan_symbol(const char* symbol) {
    // For now, just run full scan and filter
    auto all = scan();
    std::vector<ArbitrageOpportunity> filtered;
    for (const auto& opp : all) {
        if (std::strcmp(opp.symbol, symbol) == 0) {
            filtered.push_back(opp);
        }
    }
    return filtered;
}

} // namespace magnatrix::hft
