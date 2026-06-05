# 管线总览

| 阶段 | 模块 | 输出 |
|------|------|------|
| 输入 | `hw_annotation` loader | 未精炼 `AnnotationSample` |
| 精炼 | `pipeline/refine` | 同一类型的 `AnnotationSample`（`is_refined=True`） |
| 后续 | metadata、QA | 消费精炼后的内存对象 |

见 `docs/PIPELINE_REFINE.md`、`docs/PROJECT_LAYOUT.md`。
