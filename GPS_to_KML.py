import sys
import pandas as pd
import simplekml
import numpy as np

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 500)
kml = simplekml.Kml()


def main():
    """
    The main program takes in two arguments - input_file_path(a txt file) and output_file_path(a kml file) and converts
    the txt file to kml file
    :return:
    """
    input_file_path = sys.argv[1]
    output_file_path = sys.argv[2]
    gps_df = create_df(input_file_path)  # creates a data frame
    gps_df = clean_data(gps_df)  # cleans the data
    print('Cleaning done')
    write_to_kml(gps_df, output_file_path)  # writes to kml file


def create_df(file_path):
    """
    Reads in a txt file and creates a pandas data frame with columns representing Latitude and its direction,
    Longitude and its direction, quality and dilution.
    :param file_path:
    :return: pandas dataframe
    """
    columns = ['Lat', 'Lat_dir', 'Long', 'Long_dir', 'Quality', 'Dilution']
    speeds = []
    validity = []
    rows = []
    with open(file_path, encoding='utf-8', errors='ignore') as f:
        for line in f.readlines()[5:]:
            words = line.strip().split(",")
            if len(words) == 0 or len(words) > 15:
                continue
            elif words[0] == "$GPGGA":  # if line starts with GPGGA store lat, long, quality and dilution of precision
                if len(rows) == 0:
                    row = [words[2], words[3], words[4], words[5], words[6], words[8]]
                    speeds.append(np.nan)
                    validity.append(np.nan)
                    rows.append(row)
                else:
                    if rows[len(rows) - 1][0] is np.nan:
                        row = [words[2], words[3], words[4], words[5], words[6], words[8]]
                        rows[len(rows) - 1] = row
                    else:
                        row = [words[2], words[3], words[4], words[5], words[6], words[8]]
                        speeds.append(np.nan)
                        validity.append(np.nan)
                        rows.append(row)
            elif words[0] == "$GPRMC":  # if lines start with GPRMC store speed and validity
                if len(rows) == 0:
                    row = [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
                    speeds.append(float(words[7]) * 1.15078)
                    validity.append(words[2])
                    rows.append(row)
                else:
                    if speeds[len(speeds) - 1] is np.nan:
                        speeds[len(speeds) - 1] = float(words[7]) * 1.15078
                        validity[len(speeds) - 1] = words[2]
                    else:
                        row = [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
                        speeds.append(float(words[7]) * 1.15078)
                        validity.append(words[2])
                        rows.append(row)
            else:
                continue
    gps_df = pd.DataFrame(rows, columns=columns)
    gps_df['Speed'] = speeds  # combine both speed and validity back to dataframe
    gps_df['Validity'] = validity
    return gps_df


def write_to_kml(gps_df, output_path):
    """
    Writes all the cordinates to a kml file while adding line style and color
    :param gps_df:
    :param output_path:
    :return:
    """
    coordinates = []
    for index, row in gps_df.iterrows():
        lat = (1 if row['Lat_dir'] == 'N' else -1) * (float(row['Lat'][0:2]) + (float(row['Lat'][2:]) / 60))
        long = (1 if row['Long_dir'] == 'E' else -1) * (float(row['Long'][0:3]) + (float(row['Long'][3:]) / 60))
        speed = row['Speed']
        coordinates.append((long, lat, speed))

    kml_file = kml.newlinestring(name='line', coords=coordinates)
    kml_file.linestyle.color = simplekml.Color.cyan
    kml_file.linestyle.width = 3
    kml_file.polystyle.color = simplekml.Color.cyan
    kml_file.altitudemode = simplekml.AltitudeMode.relativetoground
    kml_file.extrude = 1

    # stores all coordinates into the output file
    with open(output_path, "w+"):
        kml.save(output_path, format=True)


def clean_data(gps_df):
    """
    Using noise removal techniques to clean the data
    :param gps_df:
    :return:
    """
    gps_df = gps_df[gps_df['Validity'] == 'A'].copy()  # checking if data is valid
    gps_df.drop_duplicates(subset=['Lat', 'Long'], inplace=True)  # dropping duplicate values at when vehicle stops
    gps_df.dropna(inplace=True)  # dropping null values
    gps_df = gps_df[gps_df['Quality'] < '5'].copy()  # checking if quality is high enough to consider
    gps_df.reset_index(drop=True, inplace=True)

    return gps_df


if __name__ == "__main__":
    main()
