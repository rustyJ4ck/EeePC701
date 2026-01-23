#!/bin/bash

# cpu 8 cores 1 min
# stress-ng --cpu 8 --timeout 60 --metrics-brief

# Memory Stress (4 workers, 1 GB total, 1 min)
# stress-ng --vm 4 --vm-bytes 256M --timeout 60 --metrics-brief

# Mixed Test (CPU + I/O + VM, 2 min)
# stress-ng --cpu 4 --io 4 --vm 2 --vm-bytes 512M --timeout 120 --metrics-brief

# all
# stress-ng --all 1 --timeout 30 --metrics-brief

# --vm-bytes 1512M --vm-bytes 2G
stress-ng --cpu 1 --vm 1 --vm-bytes 1512M --timeout 60s --metrics-brief