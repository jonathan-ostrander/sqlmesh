from __future__ import annotations

import typing as t

import duckdb
import pytest
from pytest_mock.plugin import MockerFixture
from sqlglot import exp, maybe_parse

from sqlmesh.core.context import Context
from sqlmesh.core.model import Model
from sqlmesh.core.plan import BuiltInPlanEvaluator, Plan
from sqlmesh.core.snapshot import Snapshot
from sqlmesh.utils import random_id

pytest_plugins = ["tests.common_fixtures"]


@pytest.fixture
def context(tmpdir) -> Context:
    return Context(path=str(tmpdir))


@pytest.fixture
def duck_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


@pytest.fixture()
def sushi_context_pre_scheduling(mocker: MockerFixture) -> Context:
    context, plan = init_and_plan_sushi_context(mocker)

    plan_evaluator = BuiltInPlanEvaluator(
        context.state_sync, context.snapshot_evaluator
    )
    plan_evaluator._push(plan)
    plan_evaluator._promote(plan)

    return context


@pytest.fixture()
def sushi_context(mocker: MockerFixture) -> Context:
    context, plan = init_and_plan_sushi_context(mocker)

    context.apply(plan)
    return context


def init_and_plan_sushi_context(mocker: MockerFixture) -> t.Tuple[Context, Plan]:
    sushi_context = Context(path="example")

    for snapshot in sushi_context.snapshots.values():
        snapshot.version = snapshot.fingerprint
        sushi_context.table_info_cache[snapshot.snapshot_id] = snapshot.table_info

    confirm = mocker.patch("sqlmesh.core.console.Confirm")
    confirm.ask.return_value = False

    plan = sushi_context.plan("prod", start="2022-01-01", end="2022-01-07")

    return (sushi_context, plan)


@pytest.fixture
def assert_exp_eq() -> t.Callable:
    def _assert_exp_eq(
        source: exp.Expression | str, expected: exp.Expression | str
    ) -> None:
        source_exp = maybe_parse(source)
        expected_exp = maybe_parse(expected)

        if not source_exp:
            raise ValueError(f"Could not parse {source}")
        if not expected_exp:
            raise ValueError(f"Could not parse {expected}")

        if source_exp != expected_exp:
            assert source_exp.sql(pretty=True) == expected_exp.sql(pretty=True)
            assert source_exp == expected_exp

    return _assert_exp_eq


@pytest.fixture
def make_snapshot() -> t.Callable:
    def _make_function(
        model: Model, version: t.Optional[str] = None, **kwargs
    ) -> Snapshot:
        return Snapshot.from_model(
            model,
            **{  # type: ignore
                "physical_schema": "sqlmesh",
                "models": {},
                "ttl": "in 1 week",
                **kwargs,
            },
            version=version,
        )

    return _make_function


@pytest.fixture
def random_name() -> t.Callable:
    return lambda: f"generated_{random_id()}"
