# US Health Disparities

This repository contains cleaned code that the US Health Disparities team used to generate results for their publications. The
`work` branch also provides lightweight utilities for constructing abridged life tables and decomposing life expectancy
differences across counties for shared race, sex, and age cohorts.

## Life expectancy decomposition utilities

The reusable code lives under `src/ushd` and can be imported as a regular Python package. The two main entry points are
`ushd.build_life_table`, which converts an age-specific mortality schedule into a life table, and
`ushd.decompose_between_counties`, which applies a Horiuchi stepwise replacement decomposition to compute age-specific
contributions to the life expectancy differential between two counties.

```python
from ushd import LifeTableInput, build_life_table, decompose_between_counties

# Create a life table for a given mortality schedule.
life_table = build_life_table(
    LifeTableInput(
        age_lower=[0, 1, 5],
        age_upper=[1, 5, None],
        mx=[0.005, 0.0008, 0.02],
    )
)

# Decompose the life expectancy gap between two counties for a cohort.
records = [
    {"county": "A", "race": "Black", "sex": "Female", "age_lower": 0, "age_upper": 1, "mx": 0.005},
    {"county": "A", "race": "Black", "sex": "Female", "age_lower": 1, "age_upper": 5, "mx": 0.0008},
    {"county": "A", "race": "Black", "sex": "Female", "age_lower": 5, "age_upper": None, "mx": 0.02},
    {"county": "B", "race": "Black", "sex": "Female", "age_lower": 0, "age_upper": 1, "mx": 0.006},
    {"county": "B", "race": "Black", "sex": "Female", "age_lower": 1, "age_upper": 5, "mx": 0.001},
    {"county": "B", "race": "Black", "sex": "Female", "age_lower": 5, "age_upper": None, "mx": 0.018},
]

contributions = decompose_between_counties(
    records,
    county_col="county",
    race_col="race",
    sex_col="sex",
    age_lower_col="age_lower",
    age_upper_col="age_upper",
    mx_col="mx",
    county_a="A",
    county_b="B",
    race="Black",
    sex="Female",
)

for row in contributions:
    print(row["age_lower"], row["age_upper"], row["contribution"])
```

Running the code above produces age-specific contributions whose sum equals the life expectancy gap between the counties.

## Navigating this repository

You can view the code for a particular publication by selecting the relevant branch from the dropdown menu, or by selecting a link below.

### Links to resources from IHME and the US Health Disparities Team

* [Life Expectancy - Race Ethnicity - 2022](https://github.com/ihmeuw/USHD/tree/life_expectancy_race_ethnicity_2022)
* [Cause of Death - Race Ethnicity - 2023](https://github.com/ihmeuw/USHD/tree/cause_of_death_race_ethnicity_2023)
* [HDI - Race Ethnicity - 2024](https://github.com/ihmeuw/USHD/tree/HDI_race_ethnicity_2024)
* [Ten Americas - 2024](https://github.com/ihmeuw/USHD/tree/10_americas_2024)
* [Life Expectancy - Educational Attainment - 2025](https://github.com/ihmeuw/USHD/tree/life_expectancy_educational_attainment_2025)
* [HALE - Race Ethnicity - 2025](https://github.com/ihmeuw/USHD/tree/HALE_race_ethnicity_2025)

You may find the [main IHME website here](http://www.healthdata.org).

You may find [interactive USHD visualizations here](https://vizhub.healthdata.org/subnational/usa).

## Downloading IHME GHDx data for decomposition experiments

The life table and decomposition helpers in this repository require county-level
mortality inputs. IHME distributes the publicly accessible life expectancy by
county, race, and ethnicity estimates through the [GHDx catalog](https://ghdx.healthdata.org/record/ihme-data/united-states-causes-death-life-expectancy-by-county-race-ethnicity-2000-2019).

Run the downloader script to mirror the ZIP archives referenced on the dataset
page and extract them into a local workspace:

```bash
python scripts/download_ghdx_dataset.py --output-dir data/ghdx
```

By default the script stores the original archives under
`data/ghdx/raw/` and extracts their contents into `data/ghdx/extracted/`.

Some releases require you to accept data use agreements in a web browser before
the files can be fetched programmatically. If the downloader reports HTTP 403
errors, visit the dataset page manually, complete any required acknowledgements,
and re-run the command.