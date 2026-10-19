import retailflow


def test_package_importable_with_version():
    """Baseline: the src-layout package is installed and importable."""
    assert retailflow.__version__ == "0.1.0"
