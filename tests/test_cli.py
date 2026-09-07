from app.main import build_parser


def test_cli_parses_compare_models_and_json_output():
    args = build_parser().parse_args(
        [
            "--url",
            "https://example.com",
            "--task",
            "ask",
            "--question",
            "What is this?",
            "--compare",
            "llama3.2",
            "gemma3",
            "--output",
            "json",
        ]
    )

    assert args.url == "https://example.com"
    assert args.task == "ask"
    assert args.question == "What is this?"
    assert args.compare == ["llama3.2", "gemma3"]
    assert args.output == "json"
