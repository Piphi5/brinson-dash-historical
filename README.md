## Installations
Make sure anaconda is [installed](https://www.anaconda.com/download)

## Field Site specific
Edit the coordinates on lines 12-14 to be the lat, lon, and elevation of where the ground station is.

## Running the dashboard
CD to this directory and run:
### Setup
`conda env create -f environment.yml`

### Run
`conda activate brinson-dash`
`streamlit run main.py`