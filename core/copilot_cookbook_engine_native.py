"""
copilot_cookbook_engine_native.py
MAGNATRIX-OS — Copilot Cookbook Engine

Inspired by awesome-copilot cookbooks:
Copy-paste-ready recipes with difficulty levels and explanations.
Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Recipe:
    recipe_id: str
    name: str
    description: str
    category: str
    language: str
    code: str
    explanation: str
    difficulty: str = "intermediate"
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class CopilotCookbookEngine:
    """Copy-paste-ready recipes with difficulty levels and explanations."""

    RECIPE_LIBRARY = {
        "function_calling": {
            "name": "Function Calling",
            "description": "Structured function calling with tool definitions",
            "category": "agents",
            "language": "python",
            "code": """import json\n\ndef call_function(name, args):\n    tools = {\n        "get_weather": lambda loc: {"temp": 72, "location": loc},\n    }\n    return tools.get(name, lambda **kw: {"error": "unknown"})(**args)\n\nmessage = {\n    "role": "assistant",\n    "function_call": {"name": "get_weather", "arguments": '{"location": "NYC"}'}\n}\nresult = call_function(\n    message["function_call"]["name"],\n    json.loads(message["function_call"]["arguments"])\n)\nprint(result)""",
            "explanation": "Define a tools registry, parse the function_call from the LLM response, dispatch to the correct function, and return results. This is the foundation of tool-using agents.",
            "difficulty": "beginner",
            "tags": ["agents", "tools", "functions"],
        },
        "rag_pipeline": {
            "name": "RAG Pipeline",
            "description": "Retrieval-Augmented Generation with embeddings",
            "category": "llm",
            "language": "python",
            "code": """import json, math\n\nclass SimpleRAG:\n    def __init__(self):\n        self.docs = []\n        self.embeddings = []\n    def embed(self, text):\n        return [ord(c) % 10 for c in text[:32]]\n    def cosine(self, a, b):\n        return sum(x*y for x,y in zip(a,b)) / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(x*x for x in b)) + 1e-9)\n    def add(self, doc):\n        self.docs.append(doc)\n        self.embeddings.append(self.embed(doc))\n    def query(self, q, k=1):\n        eq = self.embed(q)\n        scored = [(self.cosine(eq, e), d) for e, d in zip(self.embeddings, self.docs)]\n        return [d for _, d in sorted(scored, reverse=True)[:k]]\n\nrag = SimpleRAG()\nrag.add("Python is a programming language")\nrag.add("JavaScript runs in browsers")\nprint(rag.query("coding language"))""",
            "explanation": "Build a minimal RAG pipeline: chunk documents, create simple embeddings (here ord-based for demo), store in memory, compute cosine similarity for retrieval, then feed top-k into generation context.",
            "difficulty": "intermediate",
            "tags": ["rag", "embeddings", "retrieval"],
        },
        "streaming_response": {
            "name": "Streaming Response",
            "description": "Stream tokens to client as they arrive",
            "category": "llm",
            "language": "python",
            "code": """def stream_tokens(text, chunk_size=5):\n    for i in range(0, len(text), chunk_size):\n        yield text[i:i+chunk_size]\n\nfor chunk in stream_tokens("Hello, this is a streaming response"):\n    print(chunk, end="", flush=True)""",
            "explanation": "Use Python generators to yield chunks of text as they are produced. This is the standard pattern for SSE (Server-Sent Events) and streaming LLM outputs to clients.",
            "difficulty": "beginner",
            "tags": ["streaming", "sse", "generators"],
        },
        "prompt_chaining": {
            "name": "Prompt Chaining",
            "description": "Chain multiple prompts in sequence",
            "category": "prompting",
            "language": "python",
            "code": """def chain_prompts(input_text, *prompts):\n    result = input_text\n    for i, prompt_fn in enumerate(prompts, 1):\n        result = prompt_fn(result)\n        print(f"Step {i}: {result[:50]}...")\n    return result\n\ndef extract_entities(text):\n    return "entities: [" + ", ".join(text.split()[:3]) + "]"\n\ndef summarize(text):\n    return "Summary: " + text[:40]\n\nchain_prompts("AI is transforming software development", extract_entities, summarize)""",
            "explanation": "Break complex tasks into sequential steps where each step's output feeds the next input. This improves reliability, makes debugging easier, and allows retrying individual steps.",
            "difficulty": "intermediate",
            "tags": ["chaining", "pipeline", "prompts"],
        },
        "structured_output": {
            "name": "Structured Output",
            "description": "Enforce JSON schema output from LLM",
            "category": "llm",
            "language": "python",
            "code": """import json, re\n\ndef extract_json(text):\n    m = re.search(r'\{.*\}', text, re.DOTALL)\n    if m:\n        return json.loads(m.group())\n    return {}\n\nschema = {\n    "type": "object",\n    "properties": {\n        "name": {"type": "string"},\n        "age": {"type": "integer"},\n        "skills": {"type": "array", "items": {"type": "string"}}\n    },\n    "required": ["name", "age", "skills"]\n}\n\n# Simulated LLM response\nraw = "Here is the user info: {\"name\": \"Alice\", \"age\": 30, \"skills\": [\"Python\", \"Rust\"]}"\nprint(extract_json(raw))""",
            "explanation": "Use regex to extract JSON from LLM text, validate against a schema, and return structured data. This is essential for building reliable LLM-powered APIs and agents.",
            "difficulty": "intermediate",
            "tags": ["json", "schema", "structured"],
        },
        "agent_loop": {
            "name": "Agent Loop",
            "description": "Basic agent loop with tool use and memory",
            "category": "agents",
            "language": "python",
            "code": """class Agent:\n    def __init__(self):\n        self.memory = []\n        self.tools = {\n            "search": lambda q: f"Results for {q}",\n            "calc": lambda expr: str(eval(expr))\n        }\n    def think(self, query):\n        self.memory.append({"role": "user", "content": query})\n        if "search" in query:\n            result = self.tools["search"](query.replace("search", "").strip())\n        elif "calc" in query:\n            result = self.tools["calc"](query.replace("calc", "").strip())\n        else:\n            result = "I don't know how to do that"\n        self.memory.append({"role": "assistant", "content": result})\n        return result\n\nagent = Agent()\nprint(agent.think("search python tutorials"))\nprint(agent.think("calc 2 + 2"))""",
            "explanation": "Implement a basic agent loop: receive input, choose a tool based on intent, execute it, store the interaction in memory, and return the result. This is the foundation of all agent systems.",
            "difficulty": "beginner",
            "tags": ["agents", "loop", "tools"],
        },
        "context_window_mgmt": {
            "name": "Context Window Management",
            "description": "Manage token limits with summarization",
            "category": "llm",
            "language": "python",
            "code": """class ContextWindow:\n    def __init__(self, max_tokens=100):\n        self.max_tokens = max_tokens\n        self.messages = []\n    def add(self, msg):\n        self.messages.append(msg)\n        self._trim()\n    def _trim(self):\n        while len(str(self.messages)) > self.max_tokens:\n            oldest = self.messages.pop(0)\n            summary = self._summarize(oldest)\n            self.messages.insert(0, {"role": "system", "content": summary})\n    def _summarize(self, msg):\n        return f"Summary: {msg['content'][:30]}..."\n    def get(self):\n        return self.messages\n\ncw = ContextWindow(max_tokens=200)\ncw.add({"role": "user", "content": "This is a very long message that exceeds our token limit and needs to be summarized for efficiency"})\ncw.add({"role": "user", "content": "Short message"})\nprint(cw.get())""",
            "explanation": "Track context size, and when it exceeds a token limit, summarize or drop oldest messages. This is critical for long-running conversations and agents with limited context windows.",
            "difficulty": "advanced",
            "tags": ["context", "tokens", "memory"],
        },
        "few_shot_prompting": {
            "name": "Few-Shot Prompting",
            "description": "Guide LLM with examples in the prompt",
            "category": "prompting",
            "language": "python",
            "code": """def few_shot(examples, query):\n    prompt = "Given the examples, classify the sentiment.\n\n"\n    for ex in examples:\n        prompt += f"Text: {ex['text']}\nSentiment: {ex['label']}\n\n"\n    prompt += f"Text: {query}\nSentiment:"\n    return prompt\n\nexamples = [\n    {"text": "I love this product", "label": "positive"},\n    {"text": "This is terrible", "label": "negative"},\n    {"text": "It's okay I guess", "label": "neutral"},\n]\n\nprint(few_shot(examples, "Amazing experience!"))""",
            "explanation": "Include input-output examples in the prompt to teach the LLM the desired format and reasoning pattern. Few-shot improves accuracy on classification, extraction, and transformation tasks without fine-tuning.",
            "difficulty": "beginner",
            "tags": ["few-shot", "prompting", "examples"],
        },
    }

    def __init__(self, cookbook_dir: str = "./copilot_cookbook"):
        self.cookbook_dir = Path(cookbook_dir)
        self.cookbook_dir.mkdir(exist_ok=True)
        self.recipes: Dict[str, Recipe] = {}
        self._load()

    def _load(self) -> None:
        file = self.cookbook_dir / "recipes.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        self.recipes[rid] = Recipe(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        file = self.cookbook_dir / "recipes.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.recipes.items()}, f, indent=2)

    def add_from_library(self, recipe_id: str, new_id: Optional[str] = None) -> Optional[Recipe]:
        if recipe_id not in self.RECIPE_LIBRARY:
            return None
        info = self.RECIPE_LIBRARY[recipe_id]
        rid = new_id or recipe_id
        recipe = Recipe(
            recipe_id=rid, name=info["name"], description=info["description"],
            category=info["category"], language=info["language"], code=info["code"],
            explanation=info["explanation"], difficulty=info.get("difficulty", "intermediate"),
            tags=info.get("tags", []),
        )
        self.recipes[rid] = recipe
        self._save()
        return recipe

    def add_custom(self, recipe_id: str, name: str, description: str, category: str,
                   language: str, code: str, explanation: str,
                   difficulty: str = "intermediate", tags: Optional[List[str]] = None) -> Recipe:
        recipe = Recipe(
            recipe_id=recipe_id, name=name, description=description, category=category,
            language=language, code=code, explanation=explanation,
            difficulty=difficulty, tags=tags or [],
        )
        self.recipes[recipe_id] = recipe
        self._save()
        return recipe

    def export_recipe(self, recipe_id: str) -> Optional[str]:
        recipe = self.recipes.get(recipe_id)
        if not recipe:
            return None
        lines = [
            f"# {recipe.name}",
            f"**Difficulty:** {recipe.difficulty} | **Category:** {recipe.category} | **Language:** {recipe.language}",
            "",
            f"## Description",
            recipe.description,
            "",
            f"## Code",
            f"```{recipe.language}",
            recipe.code,
            "```",
            "",
            f"## Explanation",
            recipe.explanation,
            "",
            f"## Tags",
            ", ".join(f"`{t}`" for t in recipe.tags),
        ]
        return "\n".join(lines)

    def use_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        recipe = self.recipes.get(recipe_id)
        if not recipe:
            return None
        recipe.usage_count += 1
        self._save()
        return {
            "recipe_id": recipe_id, "name": recipe.name, "code": recipe.code,
            "explanation": recipe.explanation, "difficulty": recipe.difficulty,
        }

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        return self.recipes.get(recipe_id)

    def list_recipes(self) -> List[Recipe]:
        return list(self.recipes.values())

    def list_by_category(self, category: str) -> List[Recipe]:
        return [r for r in self.recipes.values() if r.category == category]

    def list_by_difficulty(self, difficulty: str) -> List[Recipe]:
        return [r for r in self.recipes.values() if r.difficulty == difficulty]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.recipes)
        total_usage = sum(r.usage_count for r in self.recipes.values())
        categories = list(set(r.category for r in self.recipes.values()))
        return {
            "total_recipes": total, "library_size": len(self.RECIPE_LIBRARY),
            "total_usage": total_usage, "categories": categories,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CopilotCookbookEngine", "Recipe"]