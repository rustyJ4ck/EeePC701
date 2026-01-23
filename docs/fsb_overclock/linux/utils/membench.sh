#!/bin/bash

sysbench memory --memory-oper=read --memory-total-size=1G run | grep "Total\|transfer"
sysbench memory --memory-oper=write --memory-total-size=1G run | grep "Total\|transfer"

# 100MHz
# R Total operations: 1048576 (147124.66 per second)	#1024.00 MiB transferred (143.68 MiB/sec)
# W Total operations: 1048576 (140882.05 per second)	#1024.00 MiB transferred (137.58 MiB/sec)

# 110MHz
# R Total operations: 1048576 (156086.60 per second)	#1024.00 MiB transferred (152.43 MiB/sec)
# W Total operations: 1048576 (148868.60 per second)	#1024.00 MiB transferred (145.38 MiB/sec)

# 120MHz
# R Total operations: 1048576 (168086.51 per second)	#1024.00 MiB transferred (164.15 MiB/sec)
# W Total operations: 1048576 (160498.79 per second)	#1024.00 MiB transferred (156.74 MiB/sec)
