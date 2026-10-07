"""Reader outcomes for the examples printed in GeoCSV v2.0.4."""

from pathlib import Path

import pandas as pd
import pytest

from mermaid import geocsv


EXAMPLES = Path(__file__).parents[1] / "data" / "fixtures" / "GeoCSV_v2.0.4_examples"


@pytest.mark.parametrize(
    "filename, message",
    [
        ("iris.geocsv", "line 3: field_unit has 7 fields; header has 8"),
        ("r2r.geocsv", "line 4: field_type has 8 fields; header has 9"),
    ],
)
def test_spec_examples_with_mismatched_metadata_are_rejected(
    filename: str, message: str,
) -> None:
    source = EXAMPLES / filename
    with pytest.raises(geocsv.GeoCSVError) as error:
        geocsv.read(source)
    assert str(error.value) == f"{source.resolve()}: {message}"


@pytest.mark.parametrize(
    "filename, columns, preserved_values",
    [
        (
            "minimal_iris.geocsv",
            [
                "Network", "Station", "Latitude", "Longitude", "Elevation",
                "SiteName", "StartTime", "EndTime",
            ],
            {
                "Longitude": ["-106.4572", "-106.4572"],
                "SiteName": ["Albuquerque, New Mexico, USA"] * 2,
                "StartTime": ["1989-08-29T00:00:00", "1995-07-14T00:00:00"],
            },
        ),
        (
            "event.geocsv",
            [
                "EventID", "Time", "Latitude", "Longitude", "Depth/km", "Author",
                "Catalog", "Contributor", "ContributorID", "MagType", "Magnitude",
                "MagAuthor", "EventLocationName",
            ],
            {
                "ContributorID": ["00301439", "15237974"],
                "Time": ["2010-03-01T06:27:32", "2010-03-01T06:25:56"],
                "MagAuthor": [" NNC", "JMA"],
                "EventLocationName": [
                    " TAJIKISTAN", " NEAR WEST COAST OF HONSHU, JAPAN",
                ],
            },
        ),
    ],
)
def test_untyped_spec_examples_preserve_strings(
    filename: str, columns: list[str], preserved_values: dict[str, list[str]],
) -> None:
    source = EXAMPLES / filename
    frames = geocsv.read(source)
    assert len(frames) == 1
    frame = frames[0]
    assert frame.shape == (2, len(columns))
    assert list(frame.columns) == columns
    assert all(isinstance(dtype, pd.StringDtype) for dtype in frame.dtypes)
    assert isinstance(frame.index, pd.RangeIndex)
    assert frame.index.equals(pd.RangeIndex(2, name="source_record_index"))
    assert frame.index.name == "source_record_index"
    for column, values in preserved_values.items():
        assert frame[column].tolist() == values

    metadata = frame.attrs["geocsv"]
    assert metadata.source_path == source.resolve()
    assert metadata.delimiter == "|"
    assert metadata.field_types == dict.fromkeys(columns, "")
    assert metadata.field_units == dict.fromkeys(columns, "")
    assert [comment.raw for comment in metadata.comments] == [
        "# dataset: GeoCSV 2.0", "# delimiter: |",
    ]


def test_unavco_spec_example_preserves_types_values_and_metadata() -> None:
    source = EXAMPLES / "unavco.geocsv"
    frames = geocsv.read(source)
    assert len(frames) == 1
    frame = frames[0]
    columns = [
        "ID", "station_name", "latitude", "longitude", "ellip_height",
        "session_start_time", "session_stop_time",
    ]
    types = ["string", "string", "float", "float", "float", "datetime", "datetime"]
    units = ["UTF-8", "UTF-8", "degrees_north", "degrees_east", "meters", "UTC", "UTC"]
    assert frame.shape == (5, 7)
    assert list(frame.columns) == columns
    assert all(isinstance(frame[column].dtype, pd.StringDtype) for column in columns[:2])
    assert all(frame[column].dtype == "Float64" for column in columns[2:5])
    for column in columns[5:]:
        assert pd.api.types.is_datetime64_dtype(frame[column].dtype)
        assert frame[column].dt.tz is None
    assert isinstance(frame.index, pd.RangeIndex)
    assert frame.index.equals(pd.RangeIndex(5, name="source_record_index"))
    assert frame.index.name == "source_record_index"
    assert frame["ID"].tolist() == ["ASBU", "CIHL", "CPCO", "CPCO", "CPCO"]
    assert frame["ellip_height"].tolist() == [1234.0, 4567.0, 4321.0, 222.0, 999.0]
    assert frame["longitude"].tolist() == [-121.3685, -121.1487, -121.2332, -121.2332, -121.2332]
    assert frame.loc[0, "session_start_time"] == pd.Timestamp("2011-08-18T00:00:00")
    assert frame.loc[4, "session_stop_time"] == pd.Timestamp("2013-06-10T22:11:15")

    metadata = frame.attrs["geocsv"]
    assert metadata.source_path == source.resolve()
    assert metadata.delimiter == ","
    assert metadata.field_types == dict(zip(columns, types))
    assert metadata.field_units == dict(zip(columns, units))
    source_comments = [line for line in source.read_text().splitlines() if line.startswith("#")]
    assert [comment.raw for comment in metadata.comments] == source_comments
    datum = next(comment for comment in metadata.comments if comment.key == "geodeticdatum")
    assert datum.value == "ITRF2008 epsg:1061"
