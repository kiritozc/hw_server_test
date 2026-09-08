#!/bin/bash
export ASCEND_RT_VISIBLE_DEVICES=0,1,2,3
export HCCL_EXEC_TIMEOUT=3600
export HCCL_BUFFSIZE=1024
export PYTORCH_NPU_ALLOC_CONF="expandable_segments:True"
export HCCL_OP_EXPANSION_MODE="AIV"
export OMP_NUM_THREADS=1
export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libjemalloc.so.2:$LD_PRELOAD
export TASK_QUEUE_ENABLE=1

vllm serve /data/nvme0/models/Qwen3-4B \
  --served-model-name Qwen3-4B \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 4 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --trust-remote-code \
  --async-scheduling \
  --additional-config '{"enable_cpu_binding":true}'
