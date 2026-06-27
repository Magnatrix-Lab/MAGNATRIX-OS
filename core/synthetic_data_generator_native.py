#!/usr/bin/env python3
"""
Synthetic Data Generator for MAGNATRIX-OS
========================================
Generate synthetic data for training: text, code, market data,
conversation logs. Data augmentation, balancing, privacy-preserving.
Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, random, re, string, time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


@dataclass
class SyntheticSample:
    """A generated synthetic sample."""
    sample_id: str
    data_type: str  # "text", "code", "market", "conversation"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)
    privacy_level: str = "public"  # "public", "anonymized", "private"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TextGenerator:
    """Generate synthetic text data."""
    
    def __init__(self, seed: int = None) -> None:
        if seed is not None:
            random.seed(seed)
        self._templates = {
            "question": [
                "What is {topic} and how does it work?",
                "Explain the concept of {topic} in simple terms.",
                "How does {topic} affect {related_topic}?",
                "What are the advantages of {topic}?",
            ],
            "answer": [
                "{topic} is a fundamental concept that involves {action}.",
                "In essence, {topic} works by {action}.",
                "The key principle of {topic} is {action}.",
            ],
            "statement": [
                "Recent developments in {topic} have shown {result}.",
                "Studies indicate that {topic} leads to {result}.",
                "It is widely accepted that {topic} {result}.",
            ],
        }
        self._topics = ["machine learning", "distributed systems", "data privacy", "neural networks", "cloud computing", "blockchain", "quantum computing", "cybersecurity"]
        self._actions = ["processing large datasets", "optimizing resource allocation", "learning patterns from data", "securing communications", "distributing workloads"]
        self._results = ["significant improvements in efficiency", "better scalability", "enhanced security", "reduced latency", "increased accuracy"]
    
    def generate(self, data_type: str = "question", count: int = 1) -> List[SyntheticSample]:
        samples = []
        templates = self._templates.get(data_type, self._templates["statement"])
        for i in range(count):
            template = random.choice(templates)
            topic = random.choice(self._topics)
            related = random.choice([t for t in self._topics if t != topic])
            action = random.choice(self._actions)
            result = random.choice(self._results)
            content = template.format(topic=topic, related_topic=related, action=action, result=result)
            samples.append(SyntheticSample(
                sample_id=f"text_{int(time.time())}_{i}",
                data_type="text",
                content=content,
                metadata={"template": data_type, "topic": topic},
            ))
        return samples


class CodeGenerator:
    """Generate synthetic code snippets."""
    
    def __init__(self) -> None:
        self._patterns = {
            "function": [
                "def {name}({params}):\n    {body}\n    return {return_val}",
                "def {name}({params}):\n    try:\n        {body}\n        return {return_val}\n    except Exception as e:\n        return None",
            ],
            "class": [
                "class {name}:\n    def __init__(self, {params}):\n        {init_body}\n\n    def {method}(self):\n        {body}\n        return {return_val}",
            ],
            "loop": [
                "for {var} in {iterable}:\n    {body}",
                "while {condition}:\n    {body}\n    {update}",
            ],
        }
        self._names = ["process_data", "calculate_metrics", "validate_input", "transform_features", "aggregate_results", "filter_records"]
        self._params = ["data", "config", "options", "items", "records", "values"]
        self._bodies = ["result = []", "filtered = [x for x in data if x]", "total = sum(values)", "return {k: v for k, v in data.items()}"]
    
    def generate(self, pattern_type: str = "function", count: int = 1) -> List[SyntheticSample]:
        samples = []
        patterns = self._patterns.get(pattern_type, self._patterns["function"])
        for i in range(count):
            pattern = random.choice(patterns)
            name = random.choice(self._names)
            params = ", ".join(random.sample(self._params, k=random.randint(1, 3)))
            body = random.choice(self._bodies)
            return_val = "result" if "result" in body else "data"
            content = pattern.format(name=name, params=params, body=body, return_val=return_val, var="i", iterable="range(10)", condition="True", update="break", method="run", init_body="self.data = data")
            samples.append(SyntheticSample(
                sample_id=f"code_{int(time.time())}_{i}",
                data_type="code",
                content=content,
                metadata={"pattern": pattern_type, "language": "python"},
            ))
        return samples


class MarketDataGenerator:
    """Generate synthetic market/trading data."""
    
    def __init__(self, seed: int = None) -> None:
        if seed is not None:
            random.seed(seed)
        self._symbols = ["BTCUSD", "ETHUSD", "AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA"]
    
    def generate_ticks(self, symbol: str = "", count: int = 100) -> List[SyntheticSample]:
        sym = symbol or random.choice(self._symbols)
        base_price = random.uniform(100, 50000)
        samples = []
        for i in range(count):
            price = base_price + random.gauss(0, base_price * 0.01)
            volume = random.uniform(0.1, 1000)
            tick = {
                "timestamp": time.time() + i,
                "symbol": sym,
                "price": round(price, 2),
                "volume": round(volume, 4),
                "bid": round(price - random.uniform(0, price * 0.001), 2),
                "ask": round(price + random.uniform(0, price * 0.001), 2),
            }
            samples.append(SyntheticSample(
                sample_id=f"tick_{sym}_{i}",
                data_type="market",
                content=json.dumps(tick),
                metadata={"symbol": sym, "tick_index": i},
            ))
        return samples
    
    def generate_ohlcv(self, symbol: str = "", periods: int = 50) -> List[SyntheticSample]:
        sym = symbol or random.choice(self._symbols)
        base_price = random.uniform(100, 50000)
        samples = []
        for i in range(periods):
            open_p = base_price + random.gauss(0, base_price * 0.005)
            close_p = open_p + random.gauss(0, base_price * 0.01)
            high_p = max(open_p, close_p) + random.uniform(0, base_price * 0.005)
            low_p = min(open_p, close_p) - random.uniform(0, base_price * 0.005)
            volume = random.uniform(100, 100000)
            candle = {
                "timestamp": time.time() + i * 60,
                "symbol": sym,
                "open": round(open_p, 2),
                "high": round(high_p, 2),
                "low": round(low_p, 2),
                "close": round(close_p, 2),
                "volume": round(volume, 2),
            }
            samples.append(SyntheticSample(
                sample_id=f"candle_{sym}_{i}",
                data_type="market",
                content=json.dumps(candle),
                metadata={"symbol": sym, "period": i, "type": "ohlcv"},
            ))
            base_price = close_p
        return samples


class ConversationGenerator:
    """Generate synthetic conversation logs."""
    
    def __init__(self) -> None:
        self._roles = ["user", "assistant", "system"]
        self._user_queries = [
            "What is the status of my order?",
            "Can you help me with this error?",
            "How do I configure the system?",
            "Explain the latest update.",
            "Show me the dashboard.",
        ]
        self._assistant_responses = [
            "Your order is currently being processed.",
            "The error is caused by a misconfiguration. Please check the logs.",
            "You can configure the system via the settings panel.",
            "The latest update includes performance improvements and bug fixes.",
            "The dashboard is accessible at /dashboard.",
        ]
    
    def generate(self, turn_count: int = 5) -> List[SyntheticSample]:
        samples = []
        for i in range(turn_count):
            role = "user" if i % 2 == 0 else "assistant"
            content = random.choice(self._user_queries) if role == "user" else random.choice(self._assistant_responses)
            samples.append(SyntheticSample(
                sample_id=f"conv_{int(time.time())}_{i}",
                data_type="conversation",
                content=content,
                metadata={"role": role, "turn": i},
            ))
        return samples


class DataAugmenter:
    """Augment existing data with synthetic variants."""
    
    def augment_text(self, text: str, count: int = 3) -> List[str]:
        """Augment text by synonym replacement, insertion, deletion."""
        variants = []
        words = text.split()
        for _ in range(count):
            variant = words.copy()
            if len(variant) > 3:
                # Random deletion
                if random.random() > 0.5:
                    del variant[random.randint(0, len(variant) - 1)]
                # Random insertion
                if random.random() > 0.5:
                    variant.insert(random.randint(0, len(variant)), random.choice(["very", "significantly", "notably"]))
            variants.append(" ".join(variant))
        return variants
    
    def augment_market(self, prices: List[float], count: int = 3) -> List[List[float]]:
        """Augment market data with noise."""
        variants = []
        for _ in range(count):
            noise = [p + random.gauss(0, p * 0.005) for p in prices]
            variants.append(noise)
        return variants


class PrivacyFilter:
    """Filter privacy-sensitive information from data."""
    
    def anonymize(self, text: str) -> str:
        """Anonymize PII in text."""
        # Replace emails
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        # Replace phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        # Replace SSN-like numbers
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
        # Replace names (simple heuristic: capitalized words)
        text = re.sub(r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b', '[NAME]', text)
        return text
    
    def k_anonymize(self, data: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
        """Simple k-anonymity: group and generalize."""
        if len(data) < k:
            return data
        # Generalize age to ranges
        for item in data:
            if "age" in item:
                age = item["age"]
                item["age"] = f"{age // 10 * 10}-{age // 10 * 10 + 9}"
        return data


class SyntheticDataEngine:
    """Top-level synthetic data generation engine."""
    
    def __init__(self, repo_root: str = "") -> None:
        self.repo_root = repo_root
        self.text_gen = TextGenerator()
        self.code_gen = CodeGenerator()
        self.market_gen = MarketDataGenerator()
        self.conv_gen = ConversationGenerator()
        self.augmenter = DataAugmenter()
        self.privacy = PrivacyFilter()
        self.generated_samples: List[SyntheticSample] = []
    
    def generate_text(self, count: int = 10) -> List[SyntheticSample]:
        samples = self.text_gen.generate(count=count)
        self.generated_samples.extend(samples)
        return samples
    
    def generate_code(self, count: int = 10) -> List[SyntheticSample]:
        samples = self.code_gen.generate(count=count)
        self.generated_samples.extend(samples)
        return samples
    
    def generate_market(self, symbol: str = "", tick_count: int = 100, candle_periods: int = 50) -> Dict[str, List[SyntheticSample]]:
        ticks = self.market_gen.generate_ticks(symbol, tick_count)
        candles = self.market_gen.generate_ohlcv(symbol, candle_periods)
        self.generated_samples.extend(ticks + candles)
        return {"ticks": ticks, "candles": candles}
    
    def generate_conversation(self, turns: int = 5) -> List[SyntheticSample]:
        samples = self.conv_gen.generate(turns)
        self.generated_samples.extend(samples)
        return samples
    
    def augment(self, data: str, data_type: str = "text") -> List[str]:
        if data_type == "text":
            return self.augmenter.augment_text(data)
        elif data_type == "market":
            prices = json.loads(data) if isinstance(data, str) else data
            return [json.dumps(p) for p in self.augmenter.augment_market(prices)]
        return []
    
    def anonymize(self, text: str) -> str:
        return self.privacy.anonymize(text)
    
    def balance_dataset(self, samples: List[SyntheticSample], target_type: str = "text") -> List[SyntheticSample]:
        """Balance dataset by generating more of underrepresented types."""
        type_counts = {}
        for s in samples:
            type_counts[s.data_type] = type_counts.get(s.data_type, 0) + 1
        max_count = max(type_counts.values()) if type_counts else 0
        
        balanced = samples.copy()
        for data_type, count in type_counts.items():
            if count < max_count:
                needed = max_count - count
                if data_type == "text":
                    balanced.extend(self.text_gen.generate(count=needed))
                elif data_type == "code":
                    balanced.extend(self.code_gen.generate(count=needed))
                elif data_type == "market":
                    balanced.extend(self.market_gen.generate_ticks(count=needed))
                elif data_type == "conversation":
                    balanced.extend(self.conv_gen.generate(needed))
        return balanced
    
    def get_stats(self) -> Dict[str, Any]:
        type_counts = {}
        for s in self.generated_samples:
            type_counts[s.data_type] = type_counts.get(s.data_type, 0) + 1
        return {
            "total_generated": len(self.generated_samples),
            "by_type": type_counts,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()
