# hw_server_test

Ascend 910B4 vLLM 性能测试脚本

## 测试环境

- 硬件: 4x Ascend 910B4 (64GB HBM)
- 软件: vLLM 0.26.0, vllm-ascend 0.19.1
- 模型: Qwen3-4B

## 文件说明

### 启动脚本

- `launch_Qwen3-4B_tp1.sh` - 单卡启动脚本
- `launch_Qwen3-4B_tp2.sh` - 双卡启动脚本  
- `launch_Qwen3-4B_tp4.sh` - 四卡启动脚本

### 测试脚本

- `bench_concurrent.py` - 真正并发的 benchmark 脚本

## 使用方法

### 1. 启动 vLLM 服务

```bash
# 单卡
bash launch_Qwen3-4B_tp1.sh

# 双卡
bash launch_Qwen3-4B_tp2.sh

# 四卡
bash launch_Qwen3-4B_tp4.sh
```

### 2. 运行性能测试

```bash
python3 bench_concurrent.py \
  --model Qwen3-4B \
  --num-requests 128 \
  --concurrency 128 \
  --mean-input-tokens 1000 \
  --mean-output-tokens 700 \
  --output results.json
```

## 测试结果 (128并发)

| 配置 | 吞吐量 | E2E延迟 | TTFT | ITL |
|------|--------|---------|------|-----|
| TP=1 | 2654 tok/s | 24.42s | 5265ms | 27.4ms |
| TP=2 | 2102 tok/s | 31.53s | 7056ms | 35.0ms |
| TP=4 | 1776 tok/s | 37.97s | 8557ms | 42.1ms |

## 结论

对于 Qwen3-4B 这样的小模型，单卡 (TP=1) 性能最佳，比 4 卡快 50%。
