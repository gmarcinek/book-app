### FileRouter

poetry run luigi --module luigi_pipeline.tasks.preprocessing.file_router FileRouter --file-path "docs/owu2.pdf" --local-scheduler

### PDFProcessing

poetry run luigi --module luigi_pipeline.tasks.preprocessing.pdf_processing PDFProcessing --file-path "docs/owu2.pdf" --local-scheduler

### LLMMarkdownProcessor

poetry run luigi --module luigi_pipeline.tasks.preprocessing.llm_markdown_processor LLMMarkdownProcessor --file-path "docs/owu2.pdf" --local-scheduler

### BatchResultCombinerTask

poetry run luigi --module luigi_pipeline.tasks.preprocessing.batch_result_combiner BatchResultCombinerTask --file-path "docs/owu2.pdf" --local-scheduler

### ConditionalProcessor (Full Pipeline)

poetry run luigi --module luigi_pipeline.tasks.conditional_processor ConditionalProcessor --file-path "docs/owu2.pdf" --local-scheduler

### Text Processing Demo

poetry run luigi --module luigi_pipeline.tasks.preprocessing.text_processing TextPreprocessing --file-path "docs/sample.txt" --local-scheduler

### Debug Mode

poetry run luigi --module luigi_pipeline.tasks.conditional_processor ConditionalProcessor --file-path "docs/owu2.pdf" --local-scheduler --log-level DEBUG
