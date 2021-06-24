import math
import sys
import pandas as pd
import simplekml
import numpy as np
import os
from geographiclib.geodesic import Geodesic

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 500)
kml = simplekml.Kml()

stops = set()  # set of all stops
turns = set()  # set of all turns
final_set = set()  # set of all hazards


def main():
    """
    The main method takes in an output file path as system argument and agglomerates all hazards from txt files in the
    current directory into a single kml file
    :return:
    """
    output_path = sys.argv[2]
    for filename in os.listdir('.'):
        if not filename.endswith('.TXT') and not filename.endswith('.txt'):  # checks if filename end with .txt
            continue
        file_path = filename
        print("Reading " + file_path)
        gps_df = create_df(file_path)  # creates a data frame
        gps_df = clean_data(gps_df)  # cleans the data frame
        print('cleaning done')
        process_df(gps_df)  # classifies the data
        write_to_kml()  # writes the output into kml file

    with open(output_path, "w+"):
        kml.save(output_path, format=True)


def process_df(gps_df):
    """
    Iterates the data frame and tries to classify if a point is a turn, stop or nothing
    :param gps_df:
    :return: None
    """
    for index, row in gps_df.iterrows():
        if index < 10 or index >= len(gps_df) - 10:
            continue
        turn = False
        dir = 'right'
        #  calculating time between 20 succesive points
        time = abs(gps_df.loc[index - 10]['Time'] - gps_df.loc[index + 10]['Time'])

        #  calculating lat and long values from the strings
        lat = (1 if row['Lat_dir'] == 'N' else -1) * (float(row['Lat'][0:2]) + (float(row['Lat'][2:]) / 60))
        long = (1 if row['Long_dir'] == 'E' else -1) * (float(row['Long'][0:3]) + (float(row['Long'][3:]) / 60))

        lat1 = (1 if gps_df.loc[index - 10]['Lat_dir'] == 'N' else -1) * (float(gps_df.loc[index - 10]['Lat'][0:2]) +
                                                                          (float(gps_df.loc[index - 10]['Lat'][
                                                                                 2:]) / 60))
        long1 = (1 if gps_df.loc[index - 10]['Long_dir'] == 'E' else -1) * (float(gps_df.loc[index - 10]['Long'][0:3])
                                                                            + (float(
                    gps_df.loc[index - 10]['Long'][3:]) / 60))

        lat2 = (1 if gps_df.loc[index + 10]['Lat_dir'] == 'N' else -1) * (float(gps_df.loc[index + 10]['Lat'][0:2])
                                                                          + (float(
                    gps_df.loc[index + 10]['Lat'][2:]) / 60))
        long2 = (1 if gps_df.loc[index + 10]['Long_dir'] == 'E' else -1) * (float(gps_df.loc[index + 10]['Long'][0:3])
                                                                            + (float(
                    gps_df.loc[index + 10]['Long'][3:]) / 60))

        # calculating angle between 3 points
        angle = get_bearing(lat1, long1, lat, long) - get_bearing(lat, long, lat2, long2)
        if abs(angle) > 30 and (time >= 8) and (time <= 120):
            # checking if its a right or lef turn
            if -90 < angle < -180 or 180 < angle < 360:
                dir = 'right'
            elif 0 < angle < 180:
                dir = 'left'
            turn = True
        if turn and not isPresent((dir, long, lat), True):
            turns.add((dir, long, lat))
        elif row['Speed'] <= 12:
            inc = True
            dec = True
            turn = False
            time = abs(gps_df.loc[index - 10]['Time'] - gps_df.loc[index + 10]['Time'])
            for delta in range(0, 5):
                if row['Speed'] > gps_df.loc[index - delta]['Speed']:
                    dec = False
                if row['Speed'] > gps_df.loc[index + delta]['Speed']:
                    inc = False
            if dec and inc and not isPresent(('stop', long, lat), False) and not turn and (time < 90) and (time > 10):
                stops.add((long, lat))


def get_bearing(lat1, long1, lat2, long2):
    """
    Get the angle between two points represented by latitude and longitude.
    :param lat1:
    :param long1:
    :param lat2:
    :param long2:
    :return:
    """
    lat1 = lat1 * math.pi / 180
    long1 = long1 * math.pi / 180
    lat2 = lat2 * math.pi / 180
    long2 = long2 * math.pi / 180
    brng = Geodesic.WGS84.Inverse(lat1, long1, lat2, long2)['azi1']
    # normalizing angle to lie in between 0 to 360
    if brng < 0:
        brng += 360
    return brng


def isPresent(new_val, flag):
    """
    Checks if the stop or turn has already been marked or not.
    :param new_val:
    :param flag:
    :return:
    """
    res = False
    delta = 0.001
    # iterating through the set of start and stops
    for val in stops:
        if abs(new_val[1] - val[0]) <= delta and abs(new_val[2] - val[1]) <= delta and not flag:
            res = True
        elif abs(new_val[1] - val[0]) <= delta and abs(new_val[2] - val[1]) <= delta and flag:
            stops.remove(val)
            return False
    for val in turns:
        if abs(new_val[1] - val[1]) <= delta and abs(new_val[2] - val[2]) <= delta and (new_val[0] == 'stop' or
                                                                                        val[0] == new_val[0]):
            res = True
    return res


def create_df(file_path):
    """
    Reads in a txt file and creates a pandas data frame with columns representing Latitude and its direction,
    Longitude and its direction, quality and dilution.
    :param file_path:
    :return: pandas dataframe
    """
    columns = ['Time', 'Lat', 'Lat_dir', 'Long', 'Long_dir', 'Quality', 'Dilution']
    speeds = []
    validity = []
    rows = []
    with open(file_path, encoding='utf-8', errors='ignore') as f:
        for line in f.readlines()[5:]:
            words = line.strip().split(",")
            if len(words) == 0 or len(words) > 15:
                continue
            elif words[0] == "$GPGGA":
                if len(rows) == 0:
                    row = [words[1], words[2], words[3], words[4], words[5], words[6], words[8]]
                    rows.append(row)
                    speeds.append(np.nan)
                    validity.append(np.nan)

                else:
                    if rows[len(rows) - 1][0] is np.nan:
                        row = [words[1], words[2], words[3], words[4], words[5], words[6], words[8]]
                        rows[len(rows) - 1] = row
                    else:
                        row = [words[1], words[2], words[3], words[4], words[5], words[6], words[8]]
                        speeds.append(np.nan)
                        validity.append(np.nan)
                        rows.append(row)
            elif words[0] == "$GPRMC":
                if len(rows) == 0:
                    row = [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
                    speeds.append(float(words[7]) * 1.15078)
                    validity.append(words[2])
                    rows.append(row)
                else:
                    if speeds[len(speeds) - 1] is np.nan:
                        speeds[len(speeds) - 1] = float(words[7]) * 1.15078
                        validity[len(speeds) - 1] = words[2]
                    else:
                        row = [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
                        speeds.append(float(words[7]) * 1.15078)
                        validity.append(words[2])
                        rows.append(row)
            else:
                continue
    km_DF = pd.DataFrame(rows, columns=columns)
    km_DF["Speed"] = speeds
    km_DF["Validity"] = validity
    return km_DF


def write_to_kml():
    """
        Writes all the cordinates to a kml file while adding line style and color
        :param gps_df:
        :param output_path:
        :return:
    """

    # iterating through stops and turns and writing the coords into a file
    for stop in stops:
        if stop not in final_set:
            kml_file = kml.newpoint(name='stop', coords=[stop])
            kml_file.style.labelstyle.color = simplekml.Color.purple
            final_set.add(stop)
    for turn in turns:
        if turn not in final_set:
            if turn[0] == 'right':
                kml_file = kml.newpoint(name=turn[0], coords=[(turn[1], turn[2])])
                kml_file.style.labelstyle.color = simplekml.Color.cyan
            else:
                kml_file = kml.newpoint(name=turn[0], coords=[(turn[1], turn[2])])
                kml_file.style.labelstyle.color = simplekml.Color.yellow
            final_set.add(turn)


def clean_data(gps_df):
    """
        Using noise removal techniques to clean the data
        :param gps_df:
        :return:
    """
    gps_df = gps_df[gps_df['Validity'] == 'A'].copy()
    gps_df.dropna(inplace=True)

    gps_df.drop_duplicates(subset=['Lat', 'Long'], inplace=True)
    gps_df = gps_df[gps_df['Quality'] < '5'].copy()

    times = []
    # converting UTC time format to seconds
    for index, row in gps_df.iterrows():
        times.append((float(row['Time'][0:2]) * 3600) + (float(row['Time'][2:4]) * 60) + float(row['Time'][4:6]))
    gps_df['Time'] = times

    gps_df.reset_index(drop=True, inplace=True)
    return gps_df


if __name__ == "__main__":
    main()
