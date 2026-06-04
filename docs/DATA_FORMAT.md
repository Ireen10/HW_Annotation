# 人工标注数据格式说明

## Dataloader

```python
from hw_annotation import HwAnnotationDataset

ds = HwAnnotationDataset("samples/samples.jsonl")  # 默认仅 MERGED
sample = ds[0]

sample.item_id
sample.batch
sample.image.url
sample.image.file_path
sample.scenario
sample.objects  # label, bbox_xyxy, relations

ds.guidelines_text  # 全文件共用标注说明，不挂在每条样本上
```

### 单图样本：保留 / 剔除

| 保留 | 剔除 |
|------|------|
| `scenario`、物体、`bbox_xyxy`、空间关系 | 每行重复的 `text` → `guidelines_text` |
| `item_id`、`batch`、`image` | `_annot_worker`、`_update_time`、`_labels` |
| 参考物 `reference_label` / `reference_id` | UI 字段（`color`、`points`、`selected` 等） |

类型定义见 `hw_annotation/sample.py`；`AnnotationSample.to_dict()` 仅便于调试，不是管线交付格式。

## 原始导出（平台 JSONL）

字段见 `schema/raw_export_record.schema.json`。`_annotation` 为嵌套 JSON，含 `scenario` 与 `image-fragments`。

| `relationship_type` | 中文名 |
|---------------------|--------|
| `topology` | 拓扑 |
| `image-based` | 图片 2D 方位 |
| `egocentric` | 观察者视角 |
| `orientation` | 物体朝向 |
| `allocentric` | 参考物视角 |

解析后的物体/关系结构见 `schema/normalized_annotation.schema.json`。
