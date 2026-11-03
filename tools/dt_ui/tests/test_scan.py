from ui.scan import scan_configs


def test_scan_configs_root_and_nested(tmp_path):
    cfg = tmp_path / "configs"
    (cfg / "n60").mkdir(parents=True)
    (cfg / "n60" / "n60_zlg.yaml").write_text("can: {}", encoding="utf-8")
    (cfg / "n60" / "n60_cx.yaml").write_text("can: {}", encoding="utf-8")
    (cfg / "n60" / "dtc_map.yaml").write_text("{}", encoding="utf-8")  # map 排除
    (cfg / "example_mock.yaml").write_text("can: {}", encoding="utf-8")
    entries = scan_configs(cfg)
    labels = [label for label, _p in entries]
    assert labels == ["example_mock", "n60/n60_cx", "n60/n60_zlg"]
    assert entries[1][1] == cfg / "n60" / "n60_cx.yaml"


def test_scan_configs_excludes_map_files(tmp_path):
    cfg = tmp_path / "configs"
    cfg.mkdir()
    for name in ("dtc_map.yaml", "event_map.yaml", "fimfid_map.yaml", "dem_dids.yaml"):
        (cfg / name).write_text("{}", encoding="utf-8")
    assert scan_configs(cfg) == []


def test_scan_configs_missing_dir(tmp_path):
    assert scan_configs(tmp_path / "nope") == []
