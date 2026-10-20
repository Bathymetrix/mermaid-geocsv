"""Independent association unit cases; no ignored or real source data needed."""

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

obspy = pytest.importorskip('obspy')
from mermaid.geocsv import associate
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
def test_incomplete_pair_fails(station, records):
    tr = trace(station)
    before = deepcopy(tr.stats)
    with pytest.raises(ValueError, match='requires both Latitude and Longitude'):
        associate(tr, records)
    assert tr.stats == before


def test_missing_pair_does_not_partially_modify_stream(records):
    st = obspy.Stream([trace(), trace('SYN03')])
    before = [deepcopy(tr.stats) for tr in st]
    with pytest.raises(ValueError, match='requires both'):
        associate(st, records)
    assert [tr.stats for tr in st] == before


@pytest.mark.parametrize('key,value', [
    ('geocsv', {}), ('geocsv', None),
    ('coordinates', {}),
    ('coordinates', {'latitude': 10., 'longitude': 20., 'elevation': 0.}),
    ('coordinates', {'latitude': -80.}),
])
def test_existing_destinations_fail_without_mutation(key, value, records):
    tr = trace()
    tr.stats[key] = value
    before = deepcopy(tr.stats)
    with pytest.raises(ValueError, match=f'stats.{key} already exists'):
        associate(tr, records)
    assert tr.stats == before


def test_later_trace_destination_conflict_leaves_batch_unchanged(records):
    st = obspy.Stream([trace(), trace('SYN02')])
    st[1].stats.coordinates = {}
    before = [deepcopy(tr.stats) for tr in st]
    with pytest.raises(ValueError, match='stats.coordinates already exists'):
        associate(st, records)
    assert [tr.stats for tr in st] == before


def test_core_stats_and_processing_history_are_preserved(records):
    tr = trace()
    tr.stats.calib = 2.5
    tr.stats.processing = ['existing upstream operation']
    before = deepcopy(tr.stats)
    associate(tr, records)
    for key, value in before.items():
        assert tr.stats[key] == value
    assert set(tr.stats.defaults) == {
        'network', 'station', 'location', 'channel', 'starttime', 'endtime',
        'sampling_rate', 'delta', 'npts', 'calib'}
    assert 'processing' not in trace().stats
    assert 'processing' not in tr.stats.defaults


def test_sncl_mismatch_is_not_repaired_from_geocsv(records):
    tr = trace()
    tr.stats.location = '20'
    before = deepcopy(tr.stats)
    with pytest.raises(ValueError, match='no match'):
        associate(tr, records)
    assert tr.stats == before


@pytest.mark.parametrize('location', ['', '""'])
@pytest.mark.parametrize('allow_first_segment', [False, True])
def test_known_empty_location_associates_exactly(tmp_path, location, allow_first_segment):
    source = tmp_path / 'empty_location.geocsv'
    source.write_text(FIXTURE.read_text().replace(',00,BDH,', f',{location},BDH,'))
    records = geocsv.read(source)
    assert records[0].loc[1, 'Location'] == ''
    tr = trace()
    tr.stats.location = ''
    if allow_first_segment:
        tr.data = np.arange(10, dtype=np.float32)
    before = tr.copy()
    associate(tr, records, allow_first_segment=allow_first_segment)
    assert tr.stats.geocsv.Location == ''
    assert tr.stats.geocsv.source_record_index == 1
    assert tr.stats.geocsv.association == ('first_segment' if allow_first_segment else 'one_segment')
    assert all(tr.stats[key] == value for key, value in before.stats.items())
    np.testing.assert_array_equal(tr.data, before.data)

    tr = trace()  # Populated Location is not a match for a known empty code.
    with pytest.raises(ValueError, match='no match'):
        associate(tr, records)
    assert 'geocsv' not in tr.stats


@pytest.mark.parametrize('field', ['Network', 'Station', 'Channel', 'Location'])
def test_missing_source_identity_fails_preflight_without_mutation(records, field):
    records[0].loc[1, field] = pd.NA
    tr = trace()
    if field == 'Location':
        tr.stats.location = ''
    before = tr.copy()
    with pytest.raises(ValueError, match=f'invalid event identity fields.*{field}') as exc:
        associate(tr, records)
    assert str(FIXTURE.resolve()) in str(exc.value)
    assert 'dataset 0' in str(exc.value) and 'records [1]' in str(exc.value)
    assert tr.stats == before.stats
    np.testing.assert_array_equal(tr.data, before.data)


@pytest.mark.parametrize('field', ['Network', 'Station', 'Channel'])
def test_empty_source_and_waveform_required_codes_are_rejected(records, field):
    records[0].loc[1, field] = ''
    tr = trace()
    tr.stats[field.lower()] = ''
    with pytest.raises(ValueError, match=f'invalid event identity fields.*{field}'):
        associate(tr, records)
    assert 'geocsv' not in tr.stats

    records[0].loc[1, field] = {'Network': 'MH', 'Station': 'SYN01', 'Channel': 'BDH'}[field]
    with pytest.raises(ValueError, match=f'invalid waveform identity fields.*{field}'):
        associate(tr, records)
    assert 'geocsv' not in tr.stats


def test_absent_source_location_column_is_not_an_empty_code(records):
    tr = trace()
    tr.stats.location = ''
    with pytest.raises(ValueError, match='lacks columns.*Location'):
        associate(tr, [records[0].drop(columns='Location')])
    assert 'geocsv' not in tr.stats


def test_duplicate_empty_location_rows_fail_source_preflight(records):
    records[0]['Location'] = ''
    duplicate = records[0].loc[[1]].copy()
    duplicate.loc[1, 'DataQuality'] = 'D'  # Quality cannot rescue duplicate keys.
    tr = trace('SYN02')  # The ambiguous source row is unrelated to this trace.
    tr.stats.location = ''
    with pytest.raises(ValueError, match='ambiguous duplicate GeoCSV event rows') as exc:
        associate(tr, records + [duplicate])
    assert "('MH', 'SYN01', '', 'BDH')" in str(exc.value)
    assert '(source, dataset, record)' in str(exc.value)
    assert 'geocsv' not in tr.stats


def test_same_identity_and_time_with_different_counts_can_be_unique(records):
    records[0].loc[9] = records[0].loc[1]
    records[0].loc[9, 'SampleCount'] = 8
    tr = trace()
    associate(tr, records)
    assert tr.stats.geocsv.source_record_index == 1
    tr = trace()
    tr.data = np.arange(8, dtype=np.float32)
    associate(tr, records)
    assert tr.stats.geocsv.source_record_index == 9


def test_all_matches_preflight_before_coordinate_projection(records):
    records[0].loc[1, 'Latitude'] = pd.NA
    records[0].loc[9] = records[0].loc[2]
    records[0].loc[9, 'StartTime'] += pd.Timedelta(nanoseconds=1)
    stream = obspy.Stream([trace(), trace('SYN02')])
    before = [tr.copy() for tr in stream]
    with pytest.raises(ValueError, match=r'ambiguous \(2 matches\)'):
        associate(stream, records)
    for tr, original in zip(stream, before):
        assert tr.stats == original.stats
        np.testing.assert_array_equal(tr.data, original.data)


def test_association_does_not_touch_existing_sac_headers(records):
    tr = trace()
    tr.stats.sac = {'unrelated': 'leave untouched'}
    before = deepcopy(tr.stats.sac)
    associate(tr, records)
    assert tr.stats.sac == before


def test_multiple_traces_and_quality_preservation(records):
    st = obspy.Stream([trace(), trace('SYN02')])
    st[0].stats.mseed = {'dataquality': 'D'}
    associate(st, records)
    assert st[0].stats.mseed.dataquality == 'D'
    assert st[0].stats.geocsv.DataQuality == 'Q'
    assert st[1].stats.geocsv.DataQuality == 'D'


def test_missing_quality_remains_source_missingness(records):
    records[0].loc[1, 'DataQuality'] = pd.NA
    tr = trace()
    tr.stats.mseed = {'dataquality': 'Q'}
    associate(tr, records)
    assert pd.isna(tr.stats.geocsv.DataQuality)
    assert tr.stats.mseed.dataquality == 'Q'


def test_known_empty_location_on_independently_read_miniseed(tmp_path):
    source = tmp_path / 'empty_location.geocsv'
    source.write_text(FIXTURE.read_text().replace(',00,BDH,', ',,BDH,'))
    records = geocsv.read(source)
    original = trace()
    original.stats.location = ''
    waveform = tmp_path / 'empty_location.mseed'
    original.write(str(waveform), format='MSEED', reclen=512)
    tr, = obspy.read(str(waveform))
    before = tr.copy()
    assert tr.stats.location == ''

    associate(tr, records)

    assert tr.stats.geocsv.Location == ''
    assert tr.stats.geocsv.source_record_index == 1
    assert all(tr.stats[key] == value for key, value in before.stats.items())
    np.testing.assert_array_equal(tr.data, before.data)


def test_ambiguous_and_absent_matches(records):
    tr = trace()
    with pytest.raises(ValueError, match='ambiguous'):
        associate(tr, records + records)
    assert 'geocsv' not in tr.stats
    tr.stats.location = '99'
    with pytest.raises(ValueError, match='no match'):
        associate(tr, records)


def test_incomplete_unrelated_event_does_not_block_unique_match(records):
    incomplete = records[0].loc[1].copy()
    incomplete['StartTime'] = pd.NaT
    records[0].loc[7] = incomplete

    tr = trace()
    associate(tr, records)
    assert tr.stats.geocsv.source_record_index == 1


def test_incomplete_event_is_reported_when_no_match_exists(records):
    incomplete = records[0].loc[1].copy()
    incomplete['StartTime'] = pd.NaT
    records[0].loc[7] = incomplete

    tr = trace()
    tr.stats.starttime += 10
    with pytest.raises(ValueError, match='incomplete event rows.*record.*7'):
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


@pytest.mark.parametrize('station', ['SYN01', 'SYN02'])
@pytest.mark.parametrize('offset_ns', [-100_001, -100_000, 100_000, 100_001])
def test_default_time_tolerance_is_fixed_and_inclusive(records, station, offset_ns):
    tr = trace(station)
    source_ns = tr.stats.starttime.ns
    tr.stats.starttime = obspy.UTCDateTime(ns=source_ns + offset_ns)
    if abs(offset_ns) <= 100_000:
        associate(tr, records)
        assert tr.stats.geocsv.StartTime.value == source_ns
        assert tr.stats.starttime.ns == source_ns + offset_ns
    else:
        with pytest.raises(ValueError, match='no match'):
            associate(tr, records)
        assert 'geocsv' not in tr.stats


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


@pytest.mark.parametrize('tolerance', [None, -1, float('inf'), float('nan'), 'invalid'])
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


@pytest.mark.parametrize('direction', [-1, 1])
@pytest.mark.parametrize('position', ['inside', 'endpoint', 'outside'])
def test_rate_tolerance_uses_inclusive_representable_endpoints(records, direction, position):
    source_rate = 20.0 + direction * 0.01
    if position == 'inside':
        source_rate = np.nextafter(source_rate, 20.0)
    elif position == 'outside':
        source_rate = np.nextafter(source_rate, direction * np.inf)
    records[0].loc[1, 'SampleRate'] = source_rate
    tr = trace()
    if position == 'outside':
        with pytest.raises(ValueError, match='no match'):
            associate(tr, records)
        assert 'geocsv' not in tr.stats
    else:
        associate(tr, records)
        assert tr.stats.geocsv.SampleRate == source_rate
    assert tr.stats.sampling_rate == 20.0
    assert records[0].loc[1, 'SampleRate'] == source_rate


def test_index_selects_expected_row_among_unsorted_competitors():
    records = geocsv.read(FIXTURE.with_name('indexed.geocsv'))
    tr = trace()
    tr.stats.starttime = obspy.UTCDateTime(ns=1735689600000100000)

    associate(tr, records)

    # Expected from the invented input, independently of the returned selection.
    assert tr.stats.geocsv.source_record_index == 1
    assert tr.stats.coordinates.latitude == 10.0
    assert tr.stats.geocsv.starttime_difference_seconds == 0.0001


def test_index_does_not_prefer_exact_time_over_another_eligible_row():
    records = geocsv.read(FIXTURE.with_name('indexed.geocsv'))
    records[0].loc[4, 'SampleCount'] = 4
    tr = trace()
    tr.stats.starttime = obspy.UTCDateTime(ns=1735689600000100000)
    before = tr.copy()

    with pytest.raises(ValueError, match=r'ambiguous \(2 matches\)'):
        associate(tr, records)

    assert tr.stats == before.stats
    np.testing.assert_array_equal(tr.data, before.data)


def test_time_matching_does_not_require_source_resolution_metadata(records):
    from dataclasses import replace
    records[0].attrs['geocsv'] = replace(records[0].attrs['geocsv'],
                                       datetime_resolution_ns={})
    tr = trace()
    associate(tr, records)
    assert tr.stats.geocsv.source_record_index == 1


@pytest.mark.parametrize('allow_first_segment', [False, True])
def test_standard_match_label_with_or_without_first_segment_permission(records, allow_first_segment):
    tr = trace()
    tr.stats.mseed = {'dataquality': 'M'}
    associate(tr, records, allow_first_segment=allow_first_segment)
    assert tr.stats.geocsv.association == 'one_segment'
    assert tr.stats.mseed.dataquality == 'M'


def test_first_segment_requires_opt_in_and_preserves_anchor_and_waveform(records):
    tr = trace()
    tr.data = np.arange(10, dtype=np.float32)
    tr.stats.mseed = {'dataquality': 'M'}
    before = tr.copy()
    with pytest.raises(ValueError, match='SampleCount=4 differs from npts=10') as exc:
        associate(tr, records)
    assert 'MH.SYN01.00.BDH' in str(exc.value)
    assert str(FIXTURE.resolve()) in str(exc.value)
    assert "'record': 1" in str(exc.value)
    assert tr.stats == before.stats
    associate(tr, records, allow_first_segment=True)
    assert tr.stats.geocsv.association == 'first_segment'
    assert tr.stats.geocsv.SampleCount == 4
    assert tr.stats.geocsv.DataQuality == 'Q'
    assert tr.stats.geocsv.source_record_index == 1
    assert dict(tr.stats.coordinates) == {'latitude': 10., 'longitude': 20., 'elevation': 0.}
    assert all(tr.stats[key] == value for key, value in before.stats.items())
    np.testing.assert_array_equal(tr.data, before.data)


def test_overlapping_source_ranges_count_each_sample_once(records):
    records[0].loc[7, 'StartTime'] = pd.Timestamp('2025-01-01T00:00:00.223456789Z')
    first = trace()
    second = first.copy()
    second.stats.starttime += 0.1
    second.data = np.arange(2, 8, dtype=np.float32)
    stream = obspy.Stream([first, second])
    stream.merge(method=1, misalignment_threshold=0)
    tr, = stream
    assert tr.stats.npts == 8
    associate(tr, records, allow_first_segment=True)
    assert tr.stats.geocsv.association == 'first_segment'
    assert tr.stats.geocsv.SampleCount == 4  # Anchor remains unchanged.
    assert tr.stats.coordinates.latitude == 10.0
    np.testing.assert_array_equal(tr.data, np.arange(8, dtype=np.float32))


def test_merged_coverage_rejects_ambiguous_grid_alignment(records):
    tr = trace()
    tr.data = np.arange(10, dtype=np.float32)
    with pytest.raises(ValueError, match='multiple waveform sample indices'):
        associate(tr, records, allow_first_segment=True, time_tolerance=0.05)
    assert 'geocsv' not in tr.stats


def test_exact_merged_alignment_uses_integer_nanosecond_sample_times(records):
    records[0].loc[[1, 7], 'SampleRate'] = 3.0
    records[0].loc[7, 'StartTime'] = (pd.Timestamp(TIMES['SYN01'])
                                    + pd.Timedelta(nanoseconds=1_333_333_333))
    tr = trace()
    tr.stats.sampling_rate = 3.0
    tr.data = np.arange(10, dtype=np.float32)
    associate(tr, records, allow_first_segment=True, time_tolerance=0)
    assert tr.stats.geocsv.association == 'first_segment'
    assert tr.stats.geocsv.starttime_difference_seconds == 0


def test_later_merged_count_failure_leaves_entire_batch_unchanged(records):
    first, second = trace(), trace('SYN02')
    second.data = np.arange(11, dtype=np.float32)
    stream = obspy.Stream([first, second])
    before = [tr.copy() for tr in stream]
    with pytest.raises(ValueError, match='requires exactly npts=11'):
        associate(stream, records, allow_first_segment=True)
    for tr, original in zip(stream, before):
        assert tr.stats == original.stats
        np.testing.assert_array_equal(tr.data, original.data)


@pytest.mark.parametrize('problem', ['one_short', 'one_extra', 'gap', 'off_grid',
                                    'overlap_sum', 'incomplete', 'rate', 'rate_drift'])
def test_merge_requires_exact_grid_coverage(records, problem):
    tr = trace()
    tr.data = np.arange(10, dtype=np.float32)
    if problem == 'one_short':
        tr.data = tr.data[:-1]
    elif problem == 'one_extra':
        tr.data = np.arange(11, dtype=np.float32)
    elif problem == 'gap':
        records[0].loc[7, 'StartTime'] += pd.Timedelta(milliseconds=50)
        tr.data = np.arange(11, dtype=np.float32)
    elif problem == 'off_grid':
        records[0].loc[7, 'StartTime'] += pd.Timedelta(nanoseconds=100_001)
    elif problem == 'overlap_sum':
        records[0].loc[7, 'StartTime'] -= pd.Timedelta(milliseconds=100)
        # The sum is 4 + 6 = 10, but the union contains only 8 samples.
    elif problem == 'incomplete':
        records[0].loc[7, 'SampleCount'] = pd.NA
    elif problem == 'rate':
        records[0].loc[7, 'SampleRate'] = 21
    elif problem == 'rate_drift':
        # Within 0.01 Hz, but six samples accumulate more than 100 us of drift.
        records[0].loc[7, 'SampleRate'] = 19.991
    before = tr.copy()
    with pytest.raises(ValueError, match='merged coverage'):
        associate(tr, records, allow_first_segment=True)
    assert tr.stats == before.stats
    np.testing.assert_array_equal(tr.data, before.data)


@pytest.mark.parametrize('offset_ns', [-100_000, 100_000])
def test_merged_segment_alignment_accepts_timing_boundary(records, offset_ns):
    records[0].loc[7, 'StartTime'] += pd.Timedelta(nanoseconds=offset_ns)
    tr = trace()
    tr.data = np.arange(10, dtype=np.float32)
    associate(tr, records, allow_first_segment=True)
    assert tr.stats.geocsv.association == 'first_segment'


@pytest.mark.parametrize('problem', ['short', 'rate', 'time', 'sncl', 'ambiguous',
                                    'missing_coordinates', 'missing_count', 'duration'])
def test_first_segment_permission_does_not_bypass_other_requirements(records, problem):
    tr = trace()
    tr.data = np.arange(10, dtype=np.float32)
    if problem == 'short':
        tr.data = tr.data[:2]
    elif problem == 'rate':
        tr.stats.sampling_rate = 21
    elif problem == 'time':
        tr.stats.starttime += 1
    elif problem == 'sncl':
        tr.stats.location = '99'
    elif problem == 'ambiguous':
        records = records + records
    elif problem == 'missing_coordinates':
        records[0].loc[1, 'Longitude'] = pd.NA
    elif problem == 'missing_count':
        records[0].loc[1, 'SampleCount'] = pd.NA
    elif problem == 'duration':
        # A slightly faster waveform can have more samples but less duration.
        records[0].loc[1, 'SampleCount'] = 10000
        records[0].loc[1, 'SampleRate'] = 19.991
        tr.data = np.arange(10001, dtype=np.float32)
    before = tr.copy()
    with pytest.raises(ValueError):
        associate(tr, records, allow_first_segment=True)
    assert tr.stats == before.stats
    np.testing.assert_array_equal(tr.data, before.data)


@pytest.mark.parametrize('allow_first_segment', [False, True])
def test_masked_gaps_are_not_contiguous_segments(records, allow_first_segment):
    tr = trace()
    tr.data = np.ma.array(np.arange(10, dtype=np.float32), mask=[False] * 5 + [True] + [False] * 4)
    with pytest.raises(ValueError, match='masked gaps'):
        associate(tr, records, allow_first_segment=allow_first_segment)
    assert 'geocsv' not in tr.stats


def test_mixed_batch_labels_and_failure_atomicity(records):
    first, second = trace(), trace('SYN02')
    second.data = np.arange(10, dtype=np.float32)
    bad = trace('SYN03')
    st = obspy.Stream([first, second, bad])
    before = [deepcopy(tr.stats) for tr in st]
    with pytest.raises(ValueError, match='requires both'):
        associate(st, records, allow_first_segment=True)
    assert [tr.stats for tr in st] == before
    associate(obspy.Stream([first, second]), records, allow_first_segment=True)
    assert first.stats.geocsv.association == 'one_segment'
    assert second.stats.geocsv.association == 'first_segment'
    assert first.stats.geocsv is not second.stats.geocsv


@pytest.mark.parametrize('column', ['association', 'starttime_difference_seconds'])
def test_association_columns_are_reserved(records, column):
    records[0][column] = 'source value'
    tr = trace()
    before = deepcopy(tr.stats)
    with pytest.raises(ValueError, match=f'collide.*{column}'):
        associate(tr, records)
    assert tr.stats == before


@pytest.mark.parametrize('column', ['readonly', '_types', 'keys', '__dict__'])
def test_attribdict_columns_fail_before_batch_mutation(tmp_path, column):
    # A valid GeoCSV extension must not change the attachment's container behavior.
    lines = FIXTURE.read_text().splitlines()
    lines[2] += ',string'
    lines[3] += ',unitless'
    lines[4] += f',{column}'
    for index in range(5, len(lines)):
        lines[index] += ',association'
    source = tmp_path / 'container_collision.geocsv'
    source.write_text('\n'.join(lines) + '\n')
    records = geocsv.read(source)
    original_frame = records[0].copy(deep=True)
    stream = obspy.Stream([trace(), trace('SYN02')])
    original_traces = [tr.copy() for tr in stream]

    with pytest.raises(ValueError, match='collide.*reserved ObsPy AttribDict') as exc:
        associate(stream, records)

    message = str(exc.value)
    assert repr(column) in message
    assert str(source.resolve()) in message
    assert 'dataset 0' in message
    assert 'attributes or methods' in message
    for tr, original in zip(stream, original_traces):
        assert tr.stats == original.stats
        np.testing.assert_array_equal(tr.data, original.data)
    pd.testing.assert_frame_equal(records[0], original_frame)


def test_nonreserved_extension_column_is_preserved(records):
    records[0]['ResearchNote'] = 'independent source value'
    tr = trace()

    associate(tr, records)

    assert tr.stats.geocsv.ResearchNote == 'independent source value'
    assert tr.stats.geocsv['ResearchNote'] == 'independent source value'


@pytest.mark.parametrize('allow_first_segment', [False, True])
def test_batch_starttime_differences_are_signed_and_independent(records, allow_first_segment):
    offsets_ns = [1, -1, 0]  # Deliberately unsorted; all match the same source row.
    st = obspy.Stream()
    source_time = pd.Timestamp(TIMES['SYN01'])
    for offset_ns in offsets_ns:
        tr = trace()
        if allow_first_segment:
            tr.data = np.arange(10, dtype=np.float32)
        tr.stats.starttime = obspy.UTCDateTime(ns=source_time.value + offset_ns)
        st.append(tr)
    before = [deepcopy(tr.stats) for tr in st]

    associate(st, records, allow_first_segment=allow_first_segment)

    for tr, offset_ns, original in zip(st, offsets_ns, before):
        assert tr.stats.geocsv.starttime_difference_seconds == offset_ns / 1_000_000_000
        assert tr.stats.geocsv.StartTime == source_time
        assert tr.stats.geocsv.source_record_index == 1
        assert tr.stats.geocsv.association == ('first_segment' if allow_first_segment else 'one_segment')
        assert all(tr.stats[key] == value for key, value in original.items())
    assert len({id(tr.stats.geocsv) for tr in st}) == len(st)
