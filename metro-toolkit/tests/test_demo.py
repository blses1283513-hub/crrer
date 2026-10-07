from metro_toolkit.demo import main


def test_demo_quick_runs(tmp_path):
    main(["--quick", "--out", str(tmp_path)])
    report = (tmp_path / "report.md").read_text()
    assert "## 5. Measurement system analysis" in report
    assert len(list(tmp_path.glob("*.png"))) == 7
