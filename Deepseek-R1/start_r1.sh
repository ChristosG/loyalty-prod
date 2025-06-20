docker run --rm -it --net host --ulimit memlock=-1 --ulimit stack=67108864 \
    --security-opt=label=disable --security-opt seccomp=unconfined \
    --tmpfs /tmp:exec --user root \
    --gpus "device=1" \
    --ipc=host \
    -p8000:8000 -p8001:8001 -p8002:8002 \
    --name trtllm251 \
    -v /mnt/nvme512/engines:/engines \
    -v ./tensorrtllm_backend:/trtback \
    -v /mnt/nvme2TB/engines:/engines2 \
    -v ./:/teback \
    2501  tritonserver --model-repository=/teback/r1 \
    --model-control-mode=explicit \
    --load-model=ensemble \
    --load-model=preprocessing \
    --load-model=postprocessing \
    --load-model=tensorrt_llm \
    --log-verbose=2 \
    --log-info=1 \
    --log-warning=1 \
    --log-error=1 \
    --http-port=8000 \
    --grpc-port=8001 \
    --metrics-port=8002
