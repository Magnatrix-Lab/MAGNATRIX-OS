#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include "market_data.h"
#include "order_book.h"
#include "arbitrage_detector.h"
#include "hft_engine.h"

namespace py = pybind11;
using namespace magnatrix::hft;

PYBIND11_MODULE(_hft_engine, m) {
    m.doc() = "MAGNATRIX-OS C++ HFT Engine — High-frequency trading core";

    // ── Enums ───────────────────────────────────────────────────────────────
    py::enum_<Side>(m, "Side")
        .value("BUY", Side::BUY)
        .value("SELL", Side::SELL);

    // ── Fixed-point helpers ─────────────────────────────────────────────────
    m.def("price_to_fixed", &price_to_fixed, "Convert double price to fixed-point (1e8 scale)");
    m.def("fixed_to_price", &fixed_to_price, "Convert fixed-point to double price");
    m.def("qty_to_fixed", &qty_to_fixed, "Convert double quantity to fixed-point");
    m.def("fixed_to_qty", &fixed_to_qty, "Convert fixed-point to double quantity");

    // ── PriceLevel ──────────────────────────────────────────────────────────
    py::class_<PriceLevel>(m, "PriceLevel")
        .def(py::init<PriceInt>(), py::arg("price") = 0)
        .def_readwrite("price", &PriceLevel::price)
        .def_readwrite("total_qty", &PriceLevel::total_qty)
        .def_readwrite("order_count", &PriceLevel::order_count)
        .def("__repr__", [](const PriceLevel& pl) {
            return "<PriceLevel price=" + std::to_string(fixed_to_price(pl.price))
                + " qty=" + std::to_string(fixed_to_qty(pl.total_qty)) + ">";
        });

    // ── OrderBook ───────────────────────────────────────────────────────────
    py::class_<OrderBook>(m, "OrderBook")
        .def(py::init<const char*>(), py::arg("symbol"))
        .def("update_l1", &OrderBook::update_l1,
             py::arg("bid"), py::arg("bid_qty"), py::arg("ask"), py::arg("ask_qty"), py::arg("ts"))
        .def("add_bid", &OrderBook::add_bid, py::arg("price"), py::arg("qty"))
        .def("add_ask", &OrderBook::add_ask, py::arg("price"), py::arg("qty"))
        .def("remove_bid", &OrderBook::remove_bid, py::arg("price"), py::arg("qty"))
        .def("remove_ask", &OrderBook::remove_ask, py::arg("price"), py::arg("qty"))
        .def("best_bid", &OrderBook::best_bid)
        .def("best_ask", &OrderBook::best_ask)
        .def("best_bid_qty", &OrderBook::best_bid_qty)
        .def("best_ask_qty", &OrderBook::best_ask_qty)
        .def("spread", &OrderBook::spread)
        .def("spread_bps", &OrderBook::spread_bps)
        .def("mid_price", &OrderBook::mid_price)
        .def("bids_snapshot", &OrderBook::bids_snapshot, py::arg("n") = 10)
        .def("asks_snapshot", &OrderBook::asks_snapshot, py::arg("n") = 10)
        .def("vwap_bid", &OrderBook::vwap_bid, py::arg("depth") = 5)
        .def("vwap_ask", &OrderBook::vwap_ask, py::arg("depth") = 5)
        .def("imbalance", &OrderBook::imbalance, py::arg("depth") = 5)
        .def("update_count", &OrderBook::update_count)
        .def("last_update_ts", &OrderBook::last_update_ts)
        .def("symbol", &OrderBook::symbol);

    // ── OrderBookManager ────────────────────────────────────────────────────
    py::class_<OrderBookManager>(m, "OrderBookManager")
        .def(py::init<>())
        .def("get_or_create", &OrderBookManager::get_or_create, py::return_value_policy::reference)
        .def("get", &OrderBookManager::get, py::return_value_policy::reference)
        .def("remove", &OrderBookManager::remove)
        .def("size", &OrderBookManager::size)
        .def("symbols", &OrderBookManager::symbols);

    // ── ArbitrageOpportunity ────────────────────────────────────────────────
    py::class_<ArbitrageOpportunity>(m, "ArbitrageOpportunity")
        .def(py::init<>())
        .def_readwrite("symbol", &ArbitrageOpportunity::symbol)
        .def_readwrite("buy_exchange", &ArbitrageOpportunity::buy_exchange)
        .def_readwrite("sell_exchange", &ArbitrageOpportunity::sell_exchange)
        .def_readwrite("buy_price", &ArbitrageOpportunity::buy_price)
        .def_readwrite("sell_price", &ArbitrageOpportunity::sell_price)
        .def_readwrite("profit_bps", &ArbitrageOpportunity::profit_bps)
        .def_readwrite("detected_at", &ArbitrageOpportunity::detected_at)
        .def_readwrite("estimated_fees_bps", &ArbitrageOpportunity::estimated_fees_bps);

    // ── FeeSchedule ─────────────────────────────────────────────────────────
    py::class_<FeeSchedule>(m, "FeeSchedule")
        .def(py::init<double, double, double>(),
             py::arg("maker_bps") = 2.0, py::arg("taker_bps") = 5.0, py::arg("withdrawal_bps") = 0.0)
        .def_readwrite("maker_bps", &FeeSchedule::maker_bps)
        .def_readwrite("taker_bps", &FeeSchedule::taker_bps)
        .def_readwrite("withdrawal_bps", &FeeSchedule::withdrawal_bps);

    // ── ArbitrageDetector ───────────────────────────────────────────────────
    py::class_<ArbitrageDetector>(m, "ArbitrageDetector")
        .def(py::init<>())
        .def("register_book", &ArbitrageDetector::register_book,
             py::arg("exchange_id"), py::arg("symbol"), py::arg("book"))
        .def("unregister_book", &ArbitrageDetector::unregister_book)
        .def("set_fee_schedule", &ArbitrageDetector::set_fee_schedule)
        .def("set_min_profit_bps", &ArbitrageDetector::set_min_profit_bps)
        .def("scan", &ArbitrageDetector::scan)
        .def("scan_symbol", &ArbitrageDetector::scan_symbol)
        .def("scans_count", &ArbitrageDetector::scans_count)
        .def("opportunities_found", &ArbitrageDetector::opportunities_found);

    // ── HFTEngine ───────────────────────────────────────────────────────────
    py::class_<HFTEngine>(m, "HFTEngine")
        .def(py::init<>())
        .def("init", &HFTEngine::init)
        .def("shutdown", &HFTEngine::shutdown)
        .def("book_manager", &HFTEngine::book_manager, py::return_value_policy::reference)
        .def("arb_detector", &HFTEngine::arb_detector, py::return_value_policy::reference)
        .def("avg_tick_latency_ns", &HFTEngine::avg_tick_latency_ns)
        .def("max_tick_latency_ns", &HFTEngine::max_tick_latency_ns)
        .def("total_ticks_processed", &HFTEngine::total_ticks_processed)
        .def("is_running", &HFTEngine::is_running);
}
