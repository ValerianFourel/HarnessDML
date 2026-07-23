"""Idempotent decryption: expected outputs and skip-completed logic."""

from zipfile import ZipFile

from halcausal.io import decrypt


def _make_zip(tmp_path, zip_name, members):
    p = tmp_path / zip_name
    with ZipFile(p, "w") as z:
        for m in members:
            z.writestr(m, "{}")
    return p


def test_expected_outputs(tmp_path):
    z = _make_zip(tmp_path, "run_UPLOAD.zip", ["trace.json.encrypted"])
    assert decrypt.expected_outputs(z) == [tmp_path / "trace.json"]


def test_decrypt_missing_skips_completed_without_needing_the_cli(tmp_path):
    _make_zip(tmp_path, "run_UPLOAD.zip", ["trace.json.encrypted"])
    (tmp_path / "trace.json").write_text("{}")  # output already present

    # binary resolution is lazy: with nothing to do this must not require hal-decrypt
    jsons, n_new = decrypt.decrypt_missing(tmp_path)
    assert n_new == 0
    assert jsons == [tmp_path / "trace.json"]
