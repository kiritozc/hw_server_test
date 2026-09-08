#!/usr/bin/env python3
"""真正并发的 benchmark"""
import asyncio
import aiohttp
import time
import json
import argparse
import statistics

def generate_prompt(mean_tokens=1000):
    base = (
        "You are a helpful AI assistant. Please answer the following question in detail. "
        "Explain the concepts of artificial intelligence, machine learning, and deep learning. "
        "Describe how neural networks work, including forward propagation and backpropagation. "
    )
    target_chars = mean_tokens * 4
    return (base * (target_chars // len(base) + 1))[:target_chars]

async def send_request(session, sem, model, prompt, max_tokens, req_id):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": True,
        "stream_options": {"include_usage": True}
    }
    
    async with sem:
        start_time = time.time()
        first_token_time = None
        token_count = 0
        token_latencies = []
        last_token_time = None
        
        try:
            async with session.post(
                "http://localhost:8000/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    return {"error": f"HTTP {response.status}: {text[:100]}"}
                
                async for line_bytes in response.content:
                    line = line_bytes.decode('utf-8').strip()
                    if not line or not line.startswith('data: '):
                        continue
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                    except:
                        continue
                    if 'choices' in data and data['choices']:
                        choice = data['choices'][0]
                        delta = choice.get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            current_time = time.time()
                            if first_token_time is None:
                                first_token_time = current_time
                            else:
                                token_latencies.append(current_time - last_token_time)
                            last_token_time = current_time
                            token_count += 1
            
            e2e_latency = time.time() - start_time
            ttft = (first_token_time - start_time) if first_token_time else e2e_latency
            itl_avg = statistics.mean(token_latencies) if token_latencies else 0
            
            return {
                "request_id": req_id,
                "e2e_latency": e2e_latency,
                "ttft": ttft,
                "itl_avg": itl_avg,
                "output_tokens": token_count,
                "tokens_per_second": token_count / e2e_latency if e2e_latency > 0 else 0
            }
        except Exception as e:
            return {"error": str(e)}

async def run_benchmark(model, num_requests, concurrency, mean_input_tokens, mean_output_tokens, timeout=600):
    sem = asyncio.Semaphore(concurrency)
    prompt = generate_prompt(mean_input_tokens)
    
    print(f"\nRunning benchmark: model={model}, requests={num_requests}, concurrency={concurrency}")
    print(f"Input tokens: ~{mean_input_tokens}, Output tokens: ~{mean_output_tokens}")
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            send_request(session, sem, model, prompt, mean_output_tokens, i)
            for i in range(num_requests)
        ]
        results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]
    
    print(f"Completed: {len(successful)}/{num_requests}, Failed: {len(failed)}")
    print(f"Total time: {total_time:.1f}s")
    
    if failed:
        for f in failed[:3]:
            print(f"  Failed: {f['error']}")
    
    return successful, failed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--num-requests', type=int, default=32)
    parser.add_argument('--concurrency', type=int, default=1)
    parser.add_argument('--mean-input-tokens', type=int, default=1000)
    parser.add_argument('--mean-output-tokens', type=int, default=700)
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--output', default='/tmp/llmperf_results.json')
    args = parser.parse_args()
    
    successful, failed = asyncio.run(run_benchmark(
        args.model, args.num_requests, args.concurrency,
        args.mean_input_tokens, args.mean_output_tokens, args.timeout
    ))
    
    if not successful:
        print("No successful requests!")
        return
    
    # Calculate statistics
    e2e_latencies = [r['e2e_latency'] for r in successful]
    ttft_latencies = [r['ttft'] for r in successful]
    itl_latencies = [r['itl_avg'] for r in successful]
    tps_values = [r['tokens_per_second'] for r in successful]
    output_tokens = [r['output_tokens'] for r in successful]
    
    total_tokens = sum(output_tokens)
    total_time = max(e2e_latencies)
    
    summary = {
        "model": args.model,
        "concurrency": args.concurrency,
        "num_requests": len(successful),
        "failed_requests": len(failed),
        "total_tokens": total_tokens,
        "total_time": total_time,
        "aggregate_throughput": total_tokens / total_time,
        "e2e_latency": {
            "mean": statistics.mean(e2e_latencies),
            "p50": statistics.median(e2e_latencies),
            "p90": sorted(e2e_latencies)[int(len(e2e_latencies) * 0.9)],
            "p99": sorted(e2e_latencies)[int(len(e2e_latencies) * 0.99)]
        },
        "ttft": {
            "mean": statistics.mean(ttft_latencies),
            "p50": statistics.median(ttft_latencies),
            "p90": sorted(ttft_latencies)[int(len(ttft_latencies) * 0.9)],
            "p99": sorted(ttft_latencies)[int(len(ttft_latencies) * 0.99)]
        },
        "itl": {
            "mean": statistics.mean(itl_latencies),
            "p50": statistics.median(itl_latencies),
            "p90": sorted(itl_latencies)[int(len(itl_latencies) * 0.9)],
            "p99": sorted(itl_latencies)[int(len(itl_latencies) * 0.99)]
        },
        "tokens_per_second": {
            "mean": statistics.mean(tps_values),
            "p50": statistics.median(tps_values),
            "p90": sorted(tps_values)[int(len(tps_values) * 0.9)]
        },
        "avg_output_tokens": statistics.mean(output_tokens)
    }
    
    print(f"\n{'='*60}")
    print(f"RESULTS for {args.model} @ {args.concurrency} concurrent")
    print(f"{'='*60}")
    print(f"Completed: {summary['num_requests']} requests")
    print(f"Failed: {summary['failed_requests']} requests")
    print(f"Total tokens: {summary['total_tokens']}")
    print(f"Aggregate throughput: {summary['aggregate_throughput']:.0f} tok/s")
    print()
    print(f"--- E2E Latency ---")
    print(f"  Mean: {summary['e2e_latency']['mean']:.2f}s, P50: {summary['e2e_latency']['p50']:.2f}s, P90: {summary['e2e_latency']['p90']:.2f}s, P99: {summary['e2e_latency']['p99']:.2f}s")
    print(f"--- TTFT ---")
    print(f"  Mean: {summary['ttft']['mean']*1000:.0f}ms, P50: {summary['ttft']['p50']*1000:.0f}ms, P90: {summary['ttft']['p90']*1000:.0f}ms, P99: {summary['ttft']['p99']*1000:.0f}ms")
    print(f"--- ITL ---")
    print(f"  Mean: {summary['itl']['mean']*1000:.1f}ms, P50: {summary['itl']['p50']*1000:.1f}ms, P90: {summary['itl']['p90']*1000:.1f}ms, P99: {summary['itl']['p99']*1000:.1f}ms")
    print(f"--- Throughput ---")
    print(f"  Mean: {summary['tokens_per_second']['mean']:.0f} tok/s, P50: {summary['tokens_per_second']['p50']:.0f} tok/s, P90: {summary['tokens_per_second']['p90']:.0f} tok/s")
    
    with open(args.output, 'w') as f:
        json.dump({"summary": summary, "results": successful}, f, indent=2)
    print(f"\nResults saved to {args.output}")

if __name__ == '__main__':
    main()
