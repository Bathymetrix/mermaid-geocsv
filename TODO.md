# TODO

- [ ] Make the GeoCSV format specification require that missing data be
  represented only by a case-insensitive `NaN` token (e.g., `NaN`, `nan`, or
  `NAN`) or an empty field (e.g., `,,`).
  - Reserve every case variant of `NaN` exclusively for missing data, across
    all data types, including string fields. It is not a legitimate string
    literal or meaningful data value.
  - Explicitly document the consequence: users who intend `nan` as a meaningful
    word, name, verb, or noun must choose a different value. Existing data using
    it as meaningful text will need a replacement to comply with this rule.
