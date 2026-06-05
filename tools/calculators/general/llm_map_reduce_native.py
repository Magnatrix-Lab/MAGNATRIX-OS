"""Map-Reduce Engine — native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Iterator
from collections import defaultdict
import itertools

@dataclass
class MapReduceJob:
    job_id: str
    mapper: Callable[[Any], Iterator[tuple]]
    reducer: Callable[[Any, List[Any]], Any]
    input_data: List[Any] = field(default_factory=list)
    chunks: List[List[Any]] = field(default_factory=list)
    intermediate: Dict[Any, List[Any]] = field(default_factory=list)
    output: Dict[Any, Any] = field(default_factory=dict)

class MapReduceEngine:
    def __init__(self, num_chunks: int = 4):
        self.num_chunks = num_chunks
        self.jobs: Dict[str, MapReduceJob] = {}

    def _chunk_data(self, data: List[Any]) -> List[List[Any]]:
        n = max(1, len(data) // self.num_chunks)
        return [data[i:i+n] for i in range(0, len(data), n)] or [[]]

    def submit(self, job_id: str, mapper: Callable, reducer: Callable, data: List[Any]) -> MapReduceJob:
        job = MapReduceJob(job_id, mapper, reducer, data)
        job.chunks = self._chunk_data(data)
        self.jobs[job_id] = job
        return job

    def run(self, job_id: str) -> Dict:
        job = self.jobs[job_id]
        # Map phase
        intermediate = defaultdict(list)
        for chunk in job.chunks:
            for item in chunk:
                for key, val in job.mapper(item):
                    intermediate[key].append(val)
        job.intermediate = dict(intermediate)
        # Reduce phase
        for key, values in intermediate.items():
            job.output[key] = job.reducer(key, values)
        return job.output

    def stats(self, job_id: str) -> Dict:
        job = self.jobs[job_id]
        return {"job_id": job_id, "chunks": len(job.chunks), "intermediate_keys": len(job.intermediate), "output_keys": len(job.output)}

def run():
    engine = MapReduceEngine(num_chunks=3)
    data = [("apple", 1), ("banana", 1), ("apple", 1), ("cherry", 1), ("banana", 1)]
    def mapper(item):
        yield item
    def reducer(key, values):
        return sum(values)
    job = engine.submit("wordcount", mapper, reducer, data)
    result = engine.run("wordcount")
    print(result)
    print(engine.stats("wordcount"))

if __name__ == "__main__":
    run()
