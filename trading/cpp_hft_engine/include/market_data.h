#pragma once
#include <cstdint>
#include <string>
#include <cstring>

namespace magnatrix::hft {

// Nanosecond-precision timestamp
using Timestamp = uint64_t;

// Side enum: 0 = Buy, 1 = Sell
enum class Side : uint8_t { BUY = 0, SELL = 1 };

// Order type
enum class OrderType : uint8_t {
    MARKET = 0,
    LIMIT = 1,
    STOP_LOSS = 2,
    TAKE_PROFIT = 3,
    STOP_LOSS_LIMIT = 4,
    TAKE_PROFIT_LIMIT = 5
};

// Order status
enum class OrderStatus : uint8_t {
    PENDING = 0,
    OPEN = 1,
    PARTIALLY_FILLED = 2,
    FILLED = 3,
    CANCELLED = 4,
    REJECTED = 5
};

// Price represented as integer (price * 1e8) for exact arithmetic
using PriceInt = int64_t;
using QuantityInt = int64_t;

// Convert double price to fixed-point
inline PriceInt price_to_fixed(double p) { return static_cast<PriceInt>(p * 1e8); }
inline double fixed_to_price(PriceInt p) { return p / 1e8; }
inline QuantityInt qty_to_fixed(double q) { return static_cast<QuantityInt>(q * 1e8); }
inline double fixed_to_qty(QuantityInt q) { return q / 1e8; }

// Market tick (L1/L2 update)
struct Tick {
    Timestamp ts;           // nanoseconds since epoch
    PriceInt price;         // last traded price
    PriceInt bid;           // best bid
    PriceInt ask;           // best ask
    QuantityInt bid_qty;    // best bid quantity
    QuantityInt ask_qty;    // best ask quantity
    QuantityInt volume;     // 24h volume
    char symbol[16];        // e.g. "BTCUSDT"
    uint8_t exchange_id;    // 0=binance, 1=bybit, 2=okx

    Tick() : ts(0), price(0), bid(0), ask(0), bid_qty(0), ask_qty(0), volume(0), exchange_id(0) {
        std::memset(symbol, 0, sizeof(symbol));
    }
};

// Trade fill event
struct TradeFill {
    Timestamp ts;
    PriceInt price;
    QuantityInt quantity;
    Side side;
    char symbol[16];
    uint8_t exchange_id;
    uint64_t trade_id;

    TradeFill() : ts(0), price(0), quantity(0), side(Side::BUY), exchange_id(0), trade_id(0) {
        std::memset(symbol, 0, sizeof(symbol));
    }
};

} // namespace magnatrix::hft
