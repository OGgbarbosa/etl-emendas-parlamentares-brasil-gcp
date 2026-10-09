import csv
import json
import os
import pathlib
import sys
from contextlib import contextmanager

import pytest

try:
    from pyspark.sql import SparkSession
    HAS_PYSPARK = True
except ImportError:
    HAS_PYSPARK = False

try:
    from databricks.connect import DatabricksSession
    from databricks.sdk import WorkspaceClient
    HAS_DB_CONNECT = True
except ImportError:
    HAS_DB_CONNECT = False


from typing import Any


@pytest.fixture()
def spark() -> Any:
    """Provide a SparkSession fixture for tests."""
    if HAS_DB_CONNECT:
        return DatabricksSession.builder.getOrCreate()
    if HAS_PYSPARK:
        return SparkSession.builder.getOrCreate()
    pytest.skip("PySpark ou Databricks Connect não estão instalados no ambiente local")


@pytest.fixture()
def load_fixture(spark: Any):
    """Provide a callable to load JSON or CSV from fixtures/ directory.

    Example usage:

        def test_using_fixture(load_fixture):
            data = load_fixture("my_data.json")
            assert data.count() >= 1
    """

    def _loader(filename: str):
        path = pathlib.Path(__file__).parent.parent / "fixtures" / filename
        suffix = path.suffix.lower()
        if suffix == ".json":
            rows = json.loads(path.read_text())
            return spark.createDataFrame(rows)
        if suffix == ".csv":
            with path.open(newline="") as f:
                rows = list(csv.DictReader(f))
            return spark.createDataFrame(rows)
        raise ValueError(f"Unsupported fixture type for: {filename}")

    return _loader


def _enable_fallback_compute():
    """Enable serverless compute if no compute is specified."""
    if not HAS_DB_CONNECT:
        return
    conf = WorkspaceClient().config
    if conf.serverless_compute_id or conf.cluster_id or os.environ.get("SPARK_REMOTE"):
        return

    url = "https://docs.databricks.com/dev-tools/databricks-connect/cluster-config"
    print("☁️ no compute specified, falling back to serverless compute", file=sys.stderr)
    print(f"  see {url} for manual configuration", file=sys.stdout)

    os.environ["DATABRICKS_SERVERLESS_COMPUTE_ID"] = "auto"


@contextmanager
def _allow_stderr_output(config: pytest.Config):
    """Temporarily disable pytest output capture."""
    capman = config.pluginmanager.get_plugin("capturemanager")
    if capman:
        with capman.global_and_fixture_disabled():
            yield
    else:
        yield


def pytest_configure(config: pytest.Config):
    """Configure pytest session."""
    if not HAS_DB_CONNECT:
        return
    try:
        with _allow_stderr_output(config):
            _enable_fallback_compute()

            # Initialize Spark session eagerly, so it is available even when
            # SparkSession.builder.getOrCreate() is used. For DB Connect 15+,
            # we validate version compatibility with the remote cluster.
            if hasattr(DatabricksSession.builder, "validateSession"):
                DatabricksSession.builder.validateSession().getOrCreate()
            else:
                DatabricksSession.builder.getOrCreate()
    except Exception as e:
        print(f"Ignorando Databricks Connect localmente/CI devido a falta de credenciais: {e}")
