# C-UAS 本体一致性验证报告

- 总结论：**通过**
- 执行时间：2026-08-12T20:27:08+08:00
- Python：3.11.15
- Java：java version "20.0.1" 2023-04-18
- Owlready2 / HermiT：0.51 / bundled

## 四层验证结果

| 检查 | 结果 | 实际证据 | 用时（秒） |
|---|---:|---|---:|
| RDF/Turtle 语法解析 | 通过 | cuas-ontology.ttl=393, cuas-data-valid.ttl=260, cuas-data-test.ttl=2, cuas-shapes.ttl=538 | 0.038 |
| 8 OT / 10 LT 结构审计 | 通过 | core_classes=8/8; core_links=10/10; unsupported_datatype_ranges=0 | 0.000 |
| 3 个扩展类型 / 6 个扩展关系审计 | 通过 | extension_classes=3/3; extension_links=6/6 | 0.000 |
| SHACL 正向实例验证 | 通过 | Conforms=True | 0.219 |
| SHACL 负向对照 | 通过 | Conforms=False; violations=2; expected_paths=priority,operationalStatus | 0.176 |
| HermiT 正向一致性 | 通过 | HermiT consistent=True; expected=True; input_triples=653 | 1.153 |
| HermiT 类型互斥负向对照 | 通过 | HermiT consistent=False; expected=False; input_triples=655 | 0.927 |

## SHACL 负向对照（期望且仅期望 2 项）

| Focus node | Path | 约束 |
|---|---|---|
| `Eq_RadarUnit_007` | `operationalStatus` | operationalStatus 必须是 Available / Engaged / Maintenance / Failed 之一 |
| `Mission_G20Summit` | `priority` | priority 必须在 [1,5] 范围内，5 为最高优先级 |

## 结论边界

- HermiT 证明的是当前 OWL 2 DL TBox 与正向 ABox 可满足；负向对照证明核心类型互斥公理能够实际检出冲突。
- SHACL 证明的是实例字段、枚举、关系方向和基数满足项目约束；它不替代描述逻辑一致性推理。
- SWRL 规则保存在独立文件，不混入 Turtle TBox；规则执行正确性应作为单独规则测试评价。

## 输入文件摘要

| 文件 | 三元组数 | SHA-256 |
|---|---:|---|
| `cuas-ontology.ttl` | 393 | `160acfb670387683249987c18ba197818d4db7481f224b048c506249b8b283b5` |
| `cuas-data-valid.ttl` | 260 | `a4a40391ab2837ffe97ee9cb92be49eae062c08355c9f8122aa1561b56b1ba5c` |
| `cuas-data-test.ttl` | 2 | `db3ddfd0fdd6186b184b5a78e7677f8b660a0a10a7d3e9f5d864c09ade17754d` |
| `cuas-shapes.ttl` | 538 | `f3804439fe628d92c8ea8da439566faf2cb92c8d00e1d8a7ad3a071e5d794b5a` |
