"""Controlled MERMAID profile: structure, typed values and immutable provenance."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path
import csv
import io

import pandas as pd
import pytest
from mermaid import geocsv

FIXTURE = Path(__file__).parent / 'fixtures/schema-1.0.0/example.geocsv'


def payload(rows=None, headers=None):
    lines = FIXTURE.read_text().splitlines(keepends=True)
    boundary = next(i for i, line in enumerate(lines) if line.startswith('MethodIdentifier,'))
    if headers is not None:
        lines[:boundary] = headers(lines[:boundary])
        boundary = next(i for i, line in enumerate(lines) if line.startswith('MethodIdentifier,'))
    if rows is not None:
        records = list(csv.reader(lines[boundary:]))
        rows(records)
        stream = io.StringIO(newline='')
        csv.writer(stream, lineterminator='\n').writerows(records)
        return (''.join(lines[:boundary]) + stream.getvalue()).encode()
    return ''.join(lines).encode()


def test_complete_example_types_order_and_provenance(tmp_path):
    source = tmp_path / 'source.geocsv'
    source.write_bytes(payload())
    frame, = geocsv.read(source)
    assert frame.shape == (8, 16)
    assert frame.index.equals(pd.RangeIndex(8, name='source_record_index'))
    assert str(frame.Time.dtype) == 'datetime64[ns, UTC]'
    assert frame.SampleCount.dtype == 'Int64'
    assert all(frame[name].dtype == 'Float64' for name in ['Latitude', 'Elevation', 'ClockOffset'])
    assert frame.Location.loc[3] == '  '
    assert frame.Location.loc[7] == '01'
    assert pd.isna(frame.WaterPressure.loc[7]) and pd.isna(frame.ClockOffset.loc[5])
    assert frame.TimeCorrectionApplied.loc[3] == -.75
    assert frame.TimeCorrectionApplied.loc[7] == 1.5
    assert frame.Elevation.loc[[3, 7]].tolist() == [0., 0.]
    metadata = frame.attrs['geocsv']
    assert metadata.source_path == source.resolve()
    assert metadata.schema_version == '1.0.0'
    assert metadata.created == '2026-10-29T00:00:00.123456Z'
    assert metadata.field_units['Elevation'] == 'meters'
    assert dict(metadata.datetime_resolution_ns['Time']) == dict.fromkeys(range(8), 1000)
    assert metadata.record_line_numbers[0] == 11
    assert deepcopy(metadata) is metadata
    with pytest.raises(TypeError):
        metadata.field_types['Time'] = 'string'
    with pytest.raises(FrozenInstanceError):
        metadata.created = 'changed'
    converted, = geocsv.read(source, datetime_timezone='Pacific/Honolulu')
    assert converted.Time.loc[0].value == frame.Time.loc[0].value


@pytest.mark.parametrize('literal', ['nan', 'NA', 'NULL', 'NaT', '01', ' comma,"quote"\n#continuation'])
def test_literal_strings_and_csv_escaping(literal):
    content = payload(rows=lambda records: [row.__setitem__(3, literal) for row in records[1:]])
    frame, = geocsv.read(content)
    assert frame.Station.tolist() == [literal] * 8
    assert frame.attrs['geocsv'].record_line_numbers[1] == (13 if '\n' in literal else 12)


@pytest.mark.parametrize('field,value', [(4, ''), (4, ' '), (9, ''), (9, '0 m'), (9, '1'), (10, ''), (10, '-1'), (12, '0'), (13, '0'), (13, '1.0'), (13, '9223372036854775808'), (15, ''), (7, '91'), (8, '-181'), (7, 'nan'), (7, 'inf'), (7, '1e999'), (7, '1e-999'), (7, ' 1'), (14, '0'), (6, 'M'), (0, 'Algorithm(event):automaid:v4'), (0, 'Derivation:Recording:'), (0, 'Derivation:Recording:automaid-'), (0, 'Derivation:Recording:automaid-v1 extra'), (11, 'MERMAID_')])
def test_invalid_recording_row(field, value):
    with pytest.raises(geocsv.GeoCSVError):
        geocsv.read(payload(rows=lambda records: records[4].__setitem__(field, value)))


@pytest.mark.parametrize('stamp', ['2026-01-01T12:00:00Z', '2026-01-01T12:00:00.000Z', '2026-01-01T12:00:00.0000000Z', '2026-01-01T12:00:00.000000', '2026-01-01T12:00:00.000000+00:00', '2026-02-30T12:00:00.000000Z', '2026-01-01T12:00:60.000000Z', '2026-01-01T24:00:00.000000Z'])
def test_invalid_time_spelling(stamp):
    with pytest.raises(geocsv.GeoCSVError):
        geocsv.read(payload(rows=lambda records: records[1].__setitem__(1, stamp)))


@pytest.mark.parametrize('key', [' MERMAID GeoCSV schema', 'dataset', 'created', 'delimiter', 'lineterminator', 'field_type', 'field_unit'])
@pytest.mark.parametrize('operation', ['missing', 'duplicate', 'wrong'])
def test_required_declarations(key, operation):
    def edit(headers):
        selected = next(line for line in headers if line.startswith(f'#{key}:'))
        if operation == 'missing': return [line for line in headers if line != selected]
        if operation == 'duplicate': return headers + [selected]
        return [line.replace(selected, selected.split(': ', 1)[0] + ': unsupported\n') for line in headers]
    with pytest.raises(geocsv.GeoCSVError):
        geocsv.read(payload(headers=edit))


@pytest.mark.parametrize('extra', ['#field_missing: \n', '#field_unknown: x\n'])
def test_unsupported_field_declarations(extra):
    with pytest.raises(geocsv.GeoCSVError):
        geocsv.read(payload(headers=lambda headers: headers + [extra]))


def test_descriptive_comments_and_absence():
    def edit(headers):
        return [line for line in headers if not line.startswith(('#description:', '#attribution:'))] + ['#opaque: untouched\n', '#opaque: repeated\n']
    frame, = geocsv.read(payload(headers=edit))
    assert [c.raw for c in frame.attrs['geocsv'].comments][-2:] == ['#opaque: untouched', '#opaque: repeated']
    assert frame.attrs['geocsv'].field_long_names == {}
    assert not any(c.key in {'description', 'attribution'} for c in frame.attrs['geocsv'].comments)


@pytest.mark.parametrize('field', [2, 3, 11])
def test_mixed_file_identity_rejected(field):
    with pytest.raises(geocsv.GeoCSVError, match='mixed'):
        geocsv.read(payload(rows=lambda rows: rows[1].__setitem__(field, 'MERMAID_other' if field == 11 else 'other')))


@pytest.mark.parametrize('mutation', [lambda b: b + b'\n', lambda b: b + b'#comment\n', lambda b: b + b'#dataset: GeoCSV\n', lambda b: b[:-1], lambda b: b.replace(b'Derivation:Recording', b'Unknown:Recording'), lambda b: b.replace(b'MethodIdentifier,Time', b'MethodIdentifier,StartTime'), lambda b: b.replace(b',seconds,seconds\n', b',seconds,meters\n')])
def test_invalid_structure(mutation):
    with pytest.raises(geocsv.GeoCSVError):
        geocsv.read(mutation(payload()))


@pytest.mark.parametrize('mutation', [lambda rows: rows[1].append(''), lambda rows: rows[1].pop(), lambda rows: rows[0].append('extra'), lambda rows: rows[0].reverse()])
def test_exact_width_and_column_order(mutation):
    with pytest.raises(geocsv.GeoCSVError):
        geocsv.read(payload(rows=mutation))


def test_equal_times_empty_optional_crlf_and_terminated_records():
    content = payload(rows=lambda rows: rows[2].__setitem__(1, rows[1][1]))
    content = content.replace(b',,,,\n', b',,,,""\n').replace(b'\n', b'\r\n')
    frame, = geocsv.read(content)
    assert frame.Time.loc[0] == frame.Time.loc[1]
    assert frame.index.tolist() == list(range(8))
    assert pd.isna(frame.TimeCorrectionApplied.loc[0])


@pytest.mark.parametrize('record', [b'"broken\n', b'not"quoted\n', b'"closed" padding\n'])
def test_malformed_quotes(record):
    prefix = payload().split(b'Measurement:Position:')[0]
    with pytest.raises(geocsv.GeoCSVError):
        geocsv.read(prefix + record)


def test_signed_gauge_measurement_is_preserved_without_changing_depth_rules():
    frame, = geocsv.read(payload(rows=lambda rows: rows[2].__setitem__(10, '-1')))
    assert frame.loc[1, 'WaterPressure'] == -1
    with pytest.raises(geocsv.GeoCSVError):
        geocsv.read(payload(rows=lambda rows: rows[3].__setitem__(10, '-1')))


@pytest.mark.parametrize('year', ['0001', '9999'])
def test_valid_gregorian_epochs_outside_nanosecond_storage_range(year):
    stamp = f'{year}-01-01T12:00:00.123456Z'
    frame, = geocsv.read(payload(rows=lambda rows: [row.__setitem__(1, stamp) for row in rows[1:]]))
    assert str(frame.Time.dtype) == 'datetime64[us, UTC]'
    assert frame.Time.iloc[0].year == int(year)
    assert frame.Time.iloc[0].microsecond == 123456
