import gradio as gr

from app.core.config import get_settings
from ui.components import (
    MODEL_CHOICES,
    question_visibility,
    refresh_health,
    refresh_observability,
    run_comparison_task,
    run_research_task,
)


def create_ui() -> gr.Blocks:
    with gr.Blocks(title="LocalAI Research Assistant") as demo:
        gr.Markdown(
            "# LocalAI Research Assistant\n"
            "Local-first AI research powered by Ollama and a FastAPI backend."
        )

        with gr.Row():
            health_status = gr.Markdown()
            refresh_button = gr.Button("Refresh Health", variant="secondary")

        refresh_button.click(fn=refresh_health, outputs=health_status)
        demo.load(fn=refresh_health, outputs=health_status)

        with gr.Tabs():
            with gr.Tab("Research"):
                with gr.Row():
                    url = gr.Textbox(
                        label="Webpage URL",
                        value="https://edwarddonner.com",
                        scale=3,
                    )
                    model = gr.Dropdown(
                        label="Model",
                        choices=MODEL_CHOICES,
                        value="llama3.2",
                    )
                    task = gr.Dropdown(
                        label="Task",
                        choices=list(["Summary", "Facts", "Topics", "Ask", "Report"]),
                        value="Summary",
                    )
                question = gr.Textbox(
                    label="Question",
                    placeholder="What does this person do?",
                    visible=False,
                )
                run_button = gr.Button("Run Research", variant="primary")
                output = gr.Markdown(label="Research Output")

                task.change(fn=question_visibility, inputs=task, outputs=question)
                run_button.click(
                    fn=run_research_task,
                    inputs=[url, task, model, question],
                    outputs=output,
                )

            with gr.Tab("Model Comparison"):
                with gr.Row():
                    compare_url = gr.Textbox(
                        label="Webpage URL",
                        value="https://edwarddonner.com",
                        scale=3,
                    )
                    compare_task = gr.Dropdown(
                        label="Task",
                        choices=list(["Summary", "Facts", "Topics", "Ask", "Report"]),
                        value="Summary",
                    )
                compare_question = gr.Textbox(
                    label="Question",
                    placeholder="What does this person do?",
                    visible=False,
                )
                compare_models = gr.CheckboxGroup(
                    label="Models",
                    choices=MODEL_CHOICES,
                    value=MODEL_CHOICES,
                )
                compare_button = gr.Button("Compare Models", variant="primary")
                comparison_output = gr.Markdown(label="Comparison Output")
                comparison_table = gr.Dataframe(label="Metrics")
                latency_chart = gr.BarPlot(
                    label="Latency By Model",
                    x="model",
                    y="latency_seconds",
                    y_title="Latency (seconds)",
                    x_title="Model",
                )

                compare_task.change(
                    fn=question_visibility,
                    inputs=compare_task,
                    outputs=compare_question,
                )
                compare_button.click(
                    fn=run_comparison_task,
                    inputs=[compare_url, compare_task, compare_models, compare_question],
                    outputs=[comparison_output, comparison_table, latency_chart],
                )

            with gr.Tab("System / Observability"):
                observability_status = gr.Markdown()
                observability_button = gr.Button("Refresh Observability", variant="secondary")
                model_metrics = gr.Dataframe(label="Model Usage And Latency")
                task_counts = gr.Dataframe(label="Task Counts")
                ingestion_counts = gr.Dataframe(label="Ingestion Method Counts")
                model_latency_chart = gr.BarPlot(
                    label="Average Model Latency",
                    x="model",
                    y="average_latency_seconds",
                    y_title="Average latency (seconds)",
                    x_title="Model",
                )
                task_count_chart = gr.BarPlot(
                    label="Requests By Task",
                    x="task",
                    y="count",
                    y_title="Requests",
                    x_title="Task",
                )

                observability_button.click(
                    fn=refresh_observability,
                    outputs=[
                        observability_status,
                        model_metrics,
                        task_counts,
                        ingestion_counts,
                        model_latency_chart,
                        task_count_chart,
                    ],
                )
                demo.load(
                    fn=refresh_observability,
                    outputs=[
                        observability_status,
                        model_metrics,
                        task_counts,
                        ingestion_counts,
                        model_latency_chart,
                        task_count_chart,
                    ],
                )

        gr.Markdown(
            "The UI calls the FastAPI backend over HTTP. Start the backend separately on "
            "`http://127.0.0.1:8000` before running research tasks."
        )
    return demo


def main() -> None:
    settings = get_settings()
    create_ui().launch(
        server_name=settings.gradio_host,
        server_port=settings.gradio_port,
        show_error=False,
    )


if __name__ == "__main__":
    main()
