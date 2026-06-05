# 标注精炼（refine）

## 核心原则

1. **同一数据结构**：精炼前后都是 `AnnotationSample` / `AnnotatedObject` / `SpatialRelation`。Loader 只忠实读原始 JSONL；`is_refined=True` 后走词表校验。
2. **主输出是内存对象**：`refine_sample` / `refine_dataset` 返回精炼后的 `AnnotationSample`，供下游 metadata、QA 直接消费；**不要**依赖再从 JSONL 读一遍。
3. **JSONL 导出可选**：`export_samples_jsonl(samples, path)` 或 CLI `--output` 仅作落盘调试。

## 精炼后新增字段

| 层级 | 字段 | 说明 |
|------|------|------|
| 物体 | `name_en` | LLM 英文物体名（标签用，非展示句） |
| 物体 | `category_en` | 英文类别（开集/闭集） |
| 物体 | `participates_in_orientation` 等 | 朝向相关标记（同前） |
| 关系 | `positional_tags` | 英文方位/拓扑**标签**（词表内 token） |
| 关系 | `positional_relationship` | 保留平台原始取值 |
| 关系 | `reference_alignment` 等 | 参考物对齐状态 |
| 样本 | `is_refined` / `refine_notes` | 精炼标记与过程说明 |

精炼完成后调用 `validate_refined_sample(sample)`（`strict_validation=True` 时失败会抛错）。

## 用法

```python
from hw_annotation import HwAnnotationDataset
from pipeline import OpenAICompatibleClient, RefineConfig, refine_dataset

raw_ds = HwAnnotationDataset("samples/samples.jsonl")
client = OpenAICompatibleClient()
refined_samples = refine_dataset(raw_ds, client=client, config=RefineConfig())

# 下游直接拿 refined_samples[i]，无需读文件
next_module.build(refined_samples)
```

```bash
# 仅内存精炼（不导出）
python -m pipeline -i samples/samples.jsonl --no-llm --no-strict

# 可选导出
python -m pipeline -i samples/samples.jsonl -o artifacts/refined.jsonl
```
