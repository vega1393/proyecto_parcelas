# Parcel Generator (PyQt6 Edition)

A modern, user-friendly application for automated parcel generation using geospatial data. This version is fully based on a PyQt6 graphical interface and is intended for end users with no command-line interaction.

## Project Structure

```
src/
  core/
  pipeline/
  ui/
  utils/
  config/
  main.py
  run_pipeline.py
resources/
tests/
requirements.txt
README.md
```

## Requirements

- Python 3.9+
- PyQt6
- geopandas
- pyogrio
- fiona
- numpy, pandas, shapely, matplotlib

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the graphical application:

```bash
python src/main.py
```

## Features
- Select input geospatial files and output directory
- Configure processing parameters (style, intensity, limits, etc.)
- Select Plan Operative (PO) file, layer, and fields
- Add or remove exclusion layers
- Monitor progress and view logs in real time
- Export results in various formats

## User Flow
1. **Select input file**: Choose a shapefile, GeoPackage, GeoJSON, or FileGDB.
2. **Select output directory**: Where results will be saved.
3. **Configure parameters**: Choose processing style and advanced options.
4. **Plan Operative (PO)**: Select PO file, layer, and fields if needed.
5. **Exclusions**: Add or remove exclusion layers as needed.
6. **Run**: Click 'Run' to start processing. Progress and logs will be shown.
7. **Results**: On completion, check the output directory for generated files.

## Example Screenshot

![screenshot](resources/screenshot.png)

## Notes
- All interface and documentation is in English.
- No CLI or Tkinter dependencies remain.
- The GUI is modern, intuitive, and robust.

## License
This project is open source and distributed under the MIT License. 