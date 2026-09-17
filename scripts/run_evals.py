"""Script to run the full benchmark evaluation dataset and print report."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_java_engineer.evaluation.benchmark_runner import BenchmarkRunner
from ai_java_engineer.llm.providers.mock_provider import MockProvider


async def main():
    print("================================================================")
    print("      AI JAVA ENGINEER - SCIENTIFIC BENCHMARK HARNESS           ")
    print("================================================================")

    dataset_path = Path(__file__).parent.parent / "evals" / "dataset.jsonl"
    tasks = BenchmarkRunner.load_dataset(dataset_path)
    print(f"Loaded {len(tasks)} benchmark tasks from {dataset_path}")

    provider = MockProvider()
    runner = BenchmarkRunner(provider=provider)

    print("\nRunning benchmark suite with hidden test evaluation...")
    report = await runner.run_benchmark(tasks)

    print("\n================ BENCHMARK REPORT ================")
    print(f"Total Tasks Evaluated:       {report.total_tasks}")
    print(f"Build Success Rate:          {report.build_success_rate * 100:.1f}%")
    print(f"Visible Test Pass Rate:      {report.visible_test_pass_rate * 100:.1f}%")
    print(f"Hidden Test Pass Rate:       {report.hidden_test_pass_rate * 100:.1f}%")
    print(f"Average Cost per Task:       ${report.average_cost_usd:.4f}")
    print(f"Average Execution Time:      {report.average_duration_seconds:.2f}s")
    print(f"Taxonomy Errors Observed:    {report.error_distribution}")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
