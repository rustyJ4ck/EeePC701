
Before fix
------------------------
$ sudo intel_reg_checker 

MI_MODE (0x209c): 0x00000200 
  (bit 14) OK:   Async Flip Performance mode
  (bit 13) OK:   Flush Performance Mode
  (bit  7) OK:   Vertex Shader Cache Mode
  (bit  6) FAIL: Vertex Shader Timer Dispatch Enable must be set   <-- FAIL

CACHE_MODE_0 (0x2120): 0x00006820 
  (bit 15) OK:   Sampler L2 Disable 
  (bit  9) PERF: Sampler L2 TLB Prefetch Enable should be set      <-- PERF
  (bit  8) OK:   Depth Related Cache Pipelined Flush Disable
  (bit  5) FAIL: STC LRA Eviction Policy must be unset             <-- FAIL
  (bit  3) OK:   Hierarchical Z Disable
  (bit  0) OK:   Render Cache Operational Flush

CACHE_MODE_1 (0x2124): 0x00000380 
  (bit 12) OK:   HIZ LRA Eviction Policy
  (bit 11) OK:   DAP Instruction and State Cache Invalidate
  (bit 10) OK:   Instruction L1 Cache and In-Flight Queue Disable
  (bit  9) FAIL: Instruction L2 Cache Fill Buffers Disable must be unset  <-- FAIL
  (bit  4) OK:   Data Disable
  (bit  1) OK:   Instruction and State L2 Cache Disable
  (bit  0) OK:   Instruction and State L1 Cache Disable

3D_CHICKEN (0x2084): 0x00000000
           OK:   chicken bits unset

3D_CHICKEN2 (0x208c): 0x01000000
           WARN: chicken bits set

ECOSKPD (0x21d0): 0x00000306
           WARN: chicken bits set


After fix
------------------------
$ sudo intel_reg_checker
MI_MODE (0x209c): 0x00000240
  (bit 14) OK:   Async Flip Performance mode
  (bit 13) OK:   Flush Performance Mode
  (bit  7) OK:   Vertex Shader Cache Mode
  (bit  6) OK:   Vertex Shader Timer Dispatch Enable
CACHE_MODE_0 (0x2120): 0x00006a00
  (bit 15) OK:   Sampler L2 Disable
  (bit  9) OK:   Sampler L2 TLB Prefetch Enable
  (bit  8) OK:   Depth Related Cache Pipelined Flush Disable
  (bit  5) OK:   STC LRA Eviction Policy
  (bit  3) OK:   Hierarchical Z Disable
  (bit  0) OK:   Render Cache Operational Flush
CACHE_MODE_1 (0x2124): 0x00000180
  (bit 12) OK:   HIZ LRA Eviction Policy
  (bit 11) OK:   DAP Instruction and State Cache Invalidate
  (bit 10) OK:   Instruction L1 Cache and In-Flight Queue Disable
  (bit  9) OK:   Instruction L2 Cache Fill Buffers Disable
  (bit  4) OK:   Data Disable
  (bit  1) OK:   Instruction and State L2 Cache Disable
  (bit  0) OK:   Instruction and State L1 Cache Disable
3D_CHICKEN (0x2084): 0x00000000
           OK:   chicken bits unset
3D_CHICKEN2 (0x208c): 0x01000000
           WARN: chicken bits set
ECOSKPD (0x21d0): 0x00000306
           WARN: chicken bits set


