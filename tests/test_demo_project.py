"""Behavior checks for Ripple's sample checkout workflow."""

import sys
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[1] / "demo_project"
sys.path.insert(0, str(DEMO_ROOT))

from checkout import checkout
from main import run
from pricing import calculate_tax, calculate_total
from receipt import print_receipt


def test_calculate_tax():
    assert calculate_tax(100) == 18


def test_calculate_total():
    assert calculate_total(100, 2) == 236


def test_checkout():
    assert checkout(100, 2) == 236


def test_print_receipt():
    assert print_receipt(100, 2) == "Total: 236.0"


def test_main_run(capsys):
    run()
    assert capsys.readouterr().out.strip() == "Total: 236.0"
