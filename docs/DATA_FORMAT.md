# 人工标注数据与 Dataloader

本文档描述**平台 JSONL 导出**、**解析规则**与 **`HwAnnotationDataset` 输出**，与 `hw_annotation/` 实现一致。后续 metadata / 训练数据管线见 `PIPELINE_NOTES.md`（方案未定）。

## 数据流

```
平台 JSONL 行 (raw_export_record)
    → iter_raw_records / HwAnnotationDataset 过滤
    → parse_sample → AnnotationSample（单图、无 UI 噪声）
```

- 类型定义：`hw_annotation/parse/sample.py`
- `_annotation` 解析：`hw_annotation/parse/normalize.py`（`parse_annotation_payload`）
- 加载：`hw_annotation/loader/`（`dataset.py`、`io.py`）
- JSON Schema：`schema/*.schema.json`（可选，`hw_annotation/utils/validate.py`）

## Dataloader：`HwAnnotationDataset`

### 基本用法

```python
from hw_annotation import HwAnnotationDataset

ds = HwAnnotationDataset("samples/samples.jsonl")
sample = ds[0]

sample.item_id
sample.batch
sample.image.url
sample.image.file_path
sample.scenario
sample.objects          # AnnotatedObject: id, label, bbox_xyxy, relations
sample.object_count     # len(objects)
sample.relation_count   # 全图关系条数之和

ds.guidelines_text      # 标注说明全文，全文件共用，不挂在每条样本上
ds.load_errors          # 解析失败的行（见下文）
list(ds)                # 或 ds.samples()
```

### 构造参数

| 参数 | 默认 | 行为 |
|------|------|------|
| `path` | — | 单个 `.jsonl` 文件，或目录下所有 `*.jsonl`（排序后依次加载） |
| `status_filter` | `("MERGED",)` | 仅保留 `_annot_status` 在集合中的行；传 `None` 表示不过滤 |
| `batch_filter` | `None` | 若设置，仅保留 `batch` 在集合中的行 |

### 加载与错误处理

- 首次访问 `len` / `[]` / `guidelines_text` / `load_errors` 时触发全量加载并缓存。
- **`guidelines_text`**：遍历源文件时，**第一条**带非空 `text` 的行即写入（与 `status_filter` 无关）。
- **`load_errors`**：某行在 `parse_sample` 中失败（如 JSON 损坏、fragment 无 `points` 等）时，记录 `"item_id (文件名): 异常"`，**该行不进入数据集**。
- 当前样本集无失败行时，`load_errors` 为空列表。

### 低层 API（不经 Dataset）

```python
from hw_annotation import iter_raw_records, load_raw_records, parse_annotation_payload, parse_sample

for record in iter_raw_records("samples/samples.jsonl"):
    ...

ann = parse_annotation_payload(record["_annotation"])  # dict: scenario, objects
sample = parse_sample(record)                         # AnnotationSample
```

## Dataloader 输出：`AnnotationSample`

每条样本对应**一张图**的一次 MERGED 标注。

### 样本级字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `item_id` | `str` | 平台任务 ID |
| `batch` | `str` | 导出批次，如 `202601301744` |
| `image` | `ImageRef` | `url`（远程地址）、`file_path`（批次内文件名） |
| `scenario` | `str` | 场景类型（来自 `_annotation.scenario`） |
| `objects` | `tuple[AnnotatedObject, ...]` | 图中所有标注物体，顺序与平台 `image-fragments` 一致 |

### 物体：`AnnotatedObject`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 平台 fragment `id` |
| `label` | `str` | `objectLabel` 去首尾空白 |
| `bbox_xyxy` | `tuple[float×4]` | 由矩形四点 `points` 取 min/max 得到 `[x1,y1,x2,y2]` |
| `relations` | `tuple[SpatialRelation, ...]` | 该物体上全部空间关系（来自 `attrs`） |

### 关系：`SpatialRelation`

| 字段 | 类型 | 说明 |
|------|------|------|
| `relationship_type` | `str` | 见下表「关系类型」 |
| `positional_relationship` | `tuple[str, ...]` | 英文枚举值，可多选（平台规则） |
| `reference_label` | `str \| None` | 平台 `reference_object` 去空白；空串为 `None` |
| `reference_id` | `str \| None` | 解析后在本图 `objects` 中按 **label 精确匹配** 得到的 `id` |
| `reference_ambiguous` | `bool` | 同 label 对应多个物体时为 `True`，此时 `reference_id` 取**第一个**匹配 id |

**参考物解析（实现要点）：**

- 仅当 `reference_label` 非空时尝试解析 `reference_id`。
- 匹配为物体 `label` 的**完全相等**，不做子串或模糊匹配（例如参考物写「床」而物体为「前方床」时，`reference_id` 为 `None`）。
- 无匹配：`reference_id` 保持 `None`，`reference_ambiguous` 为 `False`。
- Loader **不校验**关系类型与方位词表（忠实保留平台取值）；仅 JSON 解析失败、fragment 无 `points` 等结构问题会进入 `load_errors`。词表见 `constants.py`，供管线或可选 schema 校验使用。

### 调试序列化

`AnnotationSample.to_dict()` 与 `schema/annotated_sample.schema.json` 形状一致，**仅供调试**；不是管线交付格式。

## 保留 / 剔除（相对平台导出行）

| 保留在 `AnnotationSample` | 不进入样本（剔除或外置） |
|---------------------------|-------------------------|
| `item_id`、`batch`、`image`、`scenario` | 每行重复的 `text` → `guidelines_text`（数据集级） |
| 物体 `id` / `label` / `bbox_xyxy` / `relations` | `_annot_worker`、`_update_time`、`_labels` |
| 关系的 `reference_label` / `reference_id` / `reference_ambiguous` | `_annot_status`（仅作加载过滤） |
| | UI 字段：`color`、`points`、`selected`、`rotateDegree`、`isShown` 等 |

平台 `_annotation` 内字段 `reference_object` 在解析后改名为 `reference_label`。

## 关系类型与方位词表

实现词表：`hw_annotation/vocab/constants.py`（含中文展示名 `RELATIONSHIP_TYPE_ZH`、`POSITIONAL_ZH`）。

### `relationship_type`

| 值 | 中文（constants） | `positional_relationship` 允许值 |
|----|-------------------|----------------------------------|
| `topology` | 拓扑关系 | `in`, `on`, `surround` |
| `image-based` | 基于图片的位置关系 | `up`, `down`, `left`, `right`, `middle` |
| `egocentric` | 观察者视角 | `up`, `down`, `left`, `right`, `in_front_of`, `behind` |
| `orientation` | 物体朝向 | 同上（3D 方位） |
| `allocentric` | 参考对象的视角 | 同上（3D 方位） |

标注界面中文说明见各 JSONL 行的 `text` 字段（与 `guidelines_text` 相同）。

## 原始导出（平台 JSONL）

每行一条记录，字段见 `schema/raw_export_record.schema.json`。

| 字段 | 说明 |
|------|------|
| `batch`, `url`, `filePath`, `item_id` | 批次、图片 URL/文件名、任务 ID |
| `text` | 标注员可见的中文规则说明 |
| `_annot_status` | 如 `MERGED`、`DRAFT`、`SUBMITTED` |
| `_annotation` | **字符串化的 JSON**，内含 `scenario` 与 `image-fragments` |

`_annotation` 解析后的中间结构（无 `item_id` / `image`）见 `schema/normalized_annotation.schema.json`。

## Schema 与可选校验

| 文件 | 对应对象 |
|------|----------|
| `raw_export_record.schema.json` | 平台 JSONL 一行 |
| `normalized_annotation.schema.json` | `parse_annotation_payload` 的返回值 |
| `annotated_sample.schema.json` | `AnnotationSample.to_dict()` |

```python
from hw_annotation.utils.validate import validate_instance

errs = validate_instance(sample.to_dict(), "annotated_sample.schema.json")
```

需安装 `jsonschema`；未安装时返回提示信息而非抛错。

**说明：** schema 中 `objects` 要求 `minItems: 1`；若平台导出零 fragment，解析结果仍可为空列表，但 schema 校验会失败——与当前样本数据无关，属边界情况。
