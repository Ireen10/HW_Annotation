# 管线总览

| 阶段 | 模块 | 输出 |
|------|------|------|
| 输入 | `hw_annotation` loader | 未精炼 `AnnotationSample` |
| 精炼 | `pipeline/refine` | 同一类型的 `AnnotationSample`（`is_refined=True`） |
| QA（框架） | `pipeline/qa` | `AnnotationSample` 原样透传 + `qa_unrendered_records.jsonl` sidecar |
| 后续 | metadata、QA 生产逻辑 | 消费精炼后的内存对象 |

## 新增：阶段化运行框架

`python -m pipeline` 现在通过 `pipeline.runtime` 执行阶段队列：

- 每个阶段有独立 artifact（默认 `artifacts/pipeline/01_<stage>/data.jsonl`）。
- 默认支持 resume：artifact 存在则直接加载，不重复计算。
- 支持 `--from-stage <name>` 从中间阶段续跑（会读取前一阶段 artifact）。
- 默认内置一个 `refine` 阶段；可用 `--pipeline-config` 提供多阶段配置。
- `qa` 阶段已接入框架（仅占位模板/mark 结构，不含业务推理逻辑）。

### 配置示例（JSON）

```json
{
  "input_path": "samples/samples.jsonl",
  "artifacts_dir": "artifacts/pipeline",
  "stages": [
    {
      "name": "refine",
      "kind": "refine",
      "resume": true,
      "output": "data.jsonl",
      "params": {
        "use_llm": true,
        "strict_validation": false,
        "workers": 8,
        "fail_fast": false
      }
    }
  ]
}
```

见 `docs/PIPELINE_REFINE.md`、`docs/PROJECT_LAYOUT.md`。
