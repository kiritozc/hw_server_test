# Benchmark Report - Qwen Models on Ascend 910B4

## Test Configuration
- **Hardware**: 4x Ascend 910B4 (64GB HBM each)
- **Software**: vLLM 0.26.0, vllm-ascend 0.19.1
- **Test Tool**: llmperf (ray-project/llmperf)
- **Prompt**: ~1000 input tokens, 700 output tokens
- **Model**: Qwen3-4B

## Results Summary

### Qwen3-4B Performance (tokens/second)

| Concurrency | TP=2 | TP=4 | Difference |
|-------------|------|------|------------|
| 1 | 93 | 93 | +0.0% |
| 2 | 93 | - | - |
| 4 | 93 | - | - |
| 8 | 92 | 92 | +0.0% |

### Key Findings

1. **TP=2 vs TP=4**: No significant difference in throughput
2. **Small models (3-4B)**: Do not benefit from 4-card tensor parallelism
3. **Recommendation**: Use TP=2 for these models to save resources

## Conclusion

For 3-4B parameter models on Ascend 910B4:
- TP=2 is sufficient and cost-effective
- TP=4 provides no performance benefit
- The communication overhead of multi-card parallelism cancels out any computational gains for small models
