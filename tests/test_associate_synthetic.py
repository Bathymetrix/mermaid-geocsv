"""Independent association unit cases; no ignored or real source data needed."""

from copy import deepcopy
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import pytest

obspy = pytest.importorskip('obspy')
from associate import associate
from mermaid import geocsv

FIXTURE = Path(__file__).parent / 'fixtures/association/synthetic.geocsv'
TIMES = {'SYN01': '2025-01-01T00:00:00.123456789Z',
         'SYN02': '2025-01-01T00:00:01.120Z',
         'SYN03': '2025-01-01T00:00:02Z',
         'SYN04': '2025-01-01T00:00:03Z',
         'SYN05': '2025-01-01T00:00:04Z',
         'SYN06': '2025-01-01T00:00:00.001Z'}


def trace(station='SYN01'):
    start = pd.Timestamp(TIMES[station]).value
    return obspy.Trace(np.arange(4, dtype=np.float32), header={
        'network': 'MH', 'station': station, 'location': '00', 'channel': 'BDH',
        'sampling_rate': 20, 'starttime': obspy.UTCDateTime(ns=start)})


@pytest.fixture
def records():
    return geocsv.read(FIXTURE)


def test_complete_projection_and_source_snapshot(records):
    tr = trace()
    before = deepcopy(tr.stats)
    assert 'coordinates' not in tr.stats.defaults
    assert associate(tr, records) is None
    assert dict(tr.stats.coordinates) == {'latitude': 10., 'longitude': 20., 'elevation': 0.}
    assert tr.stats.geocsv.source_record_index == 1  # GPS row must not match.
    assert tr.stats.geocsv.StartTime.value == tr.stats.starttime.ns
    assert all(tr.stats[key] == value for key, value in before.items())
    records[0].loc[1, 'Latitude'] = 80
    assert tr.stats.geocsv.Latitude == 10


@pytest.mark.parametrize('station', ['SYN03', 'SYN04', 'SYN05'])
def test_incomplete_pair_fails_even_with_old_coordinates(station, records):
    tr = trace(station)
    tr.stats.coordinates = {'latitude': -80., 'longitude': 20.}
    before = deepcopy(tr.stats)
    with pytest.raises(ValueError, match='requires both Latitude and Longitude'):
        associate(tr, records)
    assert tr.stats == before


@pytest.mark.parametrize('station', ['SYN03', 'SYN04', 'SYN05'])
def test_optional_warning_skips_whole_projection(station, records):
    tr = trace(station)
    tr.stats.coordinates = {'latitude': -80., 'longitude': 20.}
    with pytest.warns(RuntimeWarning, match='coordinate projection skipped'):
        associate(tr, records, missing_coordinates='warn')
    assert 'coordinates' not in tr.stats
    assert 'geocsv' in tr.stats
    row = tr.stats.geocsv
    assert pd.isna(row.Latitude) or pd.isna(row.Longitude)


def test_missing_pair_does_not_partially_modify_stream(records):
    st = obspy.Stream([trace(), trace('SYN03')])
    before = [deepcopy(tr.stats) for tr in st]
    with pytest.raises(ValueError, match='requires both'):
        associate(st, records)
    assert [tr.stats for tr in st] == before


def test_warning_as_error_does_not_modify_stream(records):
    st = obspy.Stream([trace(), trace('SYN03')])
    before = [deepcopy(tr.stats) for tr in st]
    with warnings.catch_warnings():
        warnings.simplefilter('error', RuntimeWarning)
        with pytest.raises(RuntimeWarning):
            associate(st, records, missing_coordinates='warn')
    assert [tr.stats for tr in st] == before


def test_coordinate_conflict_fails(records):
    tr = trace()
    tr.stats.coordinates = {'latitude': -80.}
    with pytest.raises(ValueError, match='conflicting existing coordinates.latitude'):
        associate(tr, records)
    assert 'geocsv' not in tr.stats


def test_projection_starts_from_source_pair(records):
    tr = trace()
    tr.stats.coordinates = {'latitude': 10., 'longitude': 20., 'unverified': 999}
    associate(tr, records)
    assert set(tr.stats.coordinates) == {'latitude', 'longitude', 'elevation'}


def test_multiple_traces_and_quality_preservation(records):
    st = obspy.Stream([trace(), trace('SYN02')])
    st[0].stats.mseed = {'dataquality': 'D'}
    associate(st, records)
    assert st[0].stats.mseed.dataquality == 'D'
    assert st[0].stats.geocsv.DataQuality == 'Q'
    assert st[1].stats.geocsv.DataQuality == 'D'


def test_ambiguous_and_absent_matches(records):
    tr = trace()
    with pytest.raises(ValueError, match='ambiguous'):
        associate(tr, records + records)
    assert 'geocsv' not in tr.stats
    tr.stats.location = '99'
    with pytest.raises(ValueError, match='no match'):
        associate(tr, records)


@pytest.mark.parametrize('kind', ['rate', 'count'])
def test_waveform_mismatch_fails(records, kind):
    tr = trace()
    if kind == 'rate':
        tr.stats.sampling_rate = 21
    else:
        tr.data = np.arange(5, dtype=np.float32)
    with pytest.raises(ValueError, match='no match'):
        associate(tr, records)


def test_default_resolution_uses_source_digits_and_preserves_nanoseconds(records):
    tr = trace()
    tr.stats.starttime = obspy.UTCDateTime(ns=tr.stats.starttime.ns + 1)
    associate(tr, records)  # Nine source digits => 1 ns tolerance.
    assert tr.stats.geocsv.StartTime.value == pd.Timestamp(TIMES['SYN01']).value
    tr = trace()
    tr.stats.starttime = obspy.UTCDateTime(ns=tr.stats.starttime.ns + 2)
    with pytest.raises(ValueError, match='no match'):
        associate(tr, records)
    tr = trace('SYN02')
    tr.stats.starttime = obspy.UTCDateTime(ns=tr.stats.starttime.ns + 999_999)
    associate(tr, records)  # Three source digits => 1 ms tolerance.


def test_explicit_time_tolerance_overrides_default(records):
    tr = trace()
    tr.stats.starttime = obspy.UTCDateTime(ns=tr.stats.starttime.ns + 800)
    associate(tr, records, time_tolerance=0.000001)
    tr = trace()
    tr.stats.starttime = obspy.UTCDateTime(ns=tr.stats.starttime.ns + 1)
    with pytest.raises(ValueError, match='no match'):
        associate(tr, records, time_tolerance=0)


def test_writer_rounding_boundary_preserves_both_input_times(records):
    tr = trace('SYN06')
    original_ns = pd.Timestamp('2025-01-01T00:00:00Z').value + 999_600
    tr.stats.starttime = obspy.UTCDateTime(ns=original_ns)
    associate(tr, records)
    assert tr.stats.starttime.ns == original_ns
    assert tr.stats.geocsv.StartTime.value == pd.Timestamp(TIMES['SYN06']).value


@pytest.mark.parametrize('tolerance', [-1, float('inf'), float('nan'), 'invalid'])
def test_bad_tolerance_fails(records, tolerance):
    with pytest.raises(ValueError, match='finite, nonnegative'):
        associate(trace(), records, time_tolerance=tolerance)


def test_source_resolution_and_nanosecond_reader_metadata(records):
    resolution = records[0].attrs['geocsv'].datetime_resolution_ns['StartTime']
    assert resolution[1] == 1
    assert resolution[2] == 1_000_000  # .120 retains its three source digits.
    assert records[0].loc[1, 'StartTime'].value == 1735689600123456789
    with pytest.raises(TypeError):
        resolution[1] = 1000
