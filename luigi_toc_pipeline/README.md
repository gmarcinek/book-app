## Pipeline do znajdowania spisów tresci

poetry run luigi --module luigi_toc_pipeline.tasks.toc_orchestrator TOCOrchestrator --file-path "docs/owu2.pdf" --local-scheduler --log-level DEBUG

poetry run luigi --module luigi_toc_pipeline.tasks.toc_orchestrator TOCOrchestrator --file-path "docs/owu2.pdf" --local-scheduler
