from manga_optimizer import cli

from pytest import fail
from pathlib import Path

parser = cli.build_parser()

def test_defaults():
    args = parser.parse_args([
        'input',
    ])
    assert args.input_path == Path('input')
    assert args.output_path == cli.DEFAULT_OUTPUT_PATH
    assert args.formats == cli.DEFAULT_FORMATS
    assert args.flow_direction == cli.DEFAULT_FLOW_DIRECTION
    assert args.workers == cli.DEFAULT_WORKERS

def test_input_path():
    fail('not implemented')

def test_output_path():
    fail('not implemented')

def test_flow_direction():
    args = parser.parse_args([
        'input',
        '--flow-direction', 'rl'
    ])
    assert args.flow_direction == 'horizontal-rl'

    args = parser.parse_args([
        'input',
        '--flow-direction', 'lr'
    ])
    assert args.flow_direction == 'horizontal-lr'
    