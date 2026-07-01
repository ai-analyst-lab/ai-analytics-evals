# My chart judge rubric

Binary axes, same shape as the real A5 judge. A chart passes overall only if every axis passes.

rubric_version: r5

## Axes

- name: action-title
  pass: the title states the takeaway with a direction or magnitude ("Revenue grew 447% in 2024")
  fail: the title only names the axes ("Revenue by Month")

- name: focus-color
  pass: one deliberate accent color on a neutral/warm background
  fail: default matplotlib blue, or no intentional focus color

- name: direct-label
  pass: the key value is labeled directly on the data (e.g. at the end of the line)
  fail: no direct label, the reader must hunt the axis

- name: decluttered
  pass: no top/right spines, light gridlines, no busy per-point markers
  fail: full box border, heavy gridlines, marker dots on every point

- name: zero-baseline
  pass: the value axis starts at zero
  fail: the value axis starts above zero, exaggerating differences
