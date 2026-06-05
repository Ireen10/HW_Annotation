# 项目目录结构

## `hw_annotation/` — 人工标注加载

| 目录 | 职责 |
|------|------|
| `loader/` | JSONL 读取、`HwAnnotationDataset` |
| `parse/` | `_annotation` 解析、`AnnotationSample` |
| `vocab/` | 关系/方位词表（文档与可选校验） |
| `utils/` | 几何、JSON Schema 校验 |

## `pipeline/` — 下游管线

| 路径 | 职责 |
|------|------|
| `config.py` | `RefineConfig`、`LLMSettings` |
| `runtime.py` | 阶段化调度、artifact 续跑、配置加载 |
| `utils/` | 共用 LLM 客户端 |
| `refine/` | **标注精炼**：对齐参考物、英文 name/category、positional_tags、校验 |
| （后续）`metadata/`、`qa/` 等 | 按能力命名 |

## 其它

- `schema/` — JSON Schema  
- `config/` — 管线配置示例（如 `pipeline.example.yaml`）  
- `docs/` — `DATA_FORMAT.md`、`PIPELINE_REFINE.md` 等  
- `samples/`、`artifacts/`、`tests/` — 本地（`tests/` 不入库）
