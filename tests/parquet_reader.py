import os.path

import pandas as pd


def read_parquet_sensor_data(file: str) -> pd.DataFrame:
    """Read a long-format parquet file into a dataframe"""
    df = pd.read_parquet(file)

    timestamp = df["timestamp"].explode(ignore_index=True)
    type_ = df["type"].explode(ignore_index=True)
    value = df["value"].explode(ignore_index=True)

    df = pd.concat([timestamp, type_, value], axis="columns")
    return df


def get_parquet_test_data(file_name: str):
    """Pivot a long-format dataframe into groups of data points with the same sensor data type group"""
    sensor_data_type_group_map = {
        "ACCELERATION_X": "ACCELERATION",
        "ACCELERATION_Y": "ACCELERATION",
        "ACCELERATION_Z": "ACCELERATION",
        "ORIENTATION_X": "ORIENTATION",
        "ORIENTATION_Y": "ORIENTATION",
        "ORIENTATION_Z": "ORIENTATION",
        "LINEAR_ACCELERATION_X": "LINEAR_ACCELERATION",
        "LINEAR_ACCELERATION_Y": "LINEAR_ACCELERATION",
        "LINEAR_ACCELERATION_Z": "LINEAR_ACCELERATION",
        "MAGNETOMETER_X": "MAGNETOMETER",
        "MAGNETOMETER_Y": "MAGNETOMETER",
        "MAGNETOMETER_Z": "MAGNETOMETER",
        "GRAVITY_X": "GRAVITY",
        "GRAVITY_Y": "GRAVITY",
        "GRAVITY_Z": "GRAVITY",
        "LIGHT": "LIGHT",
    }
    if os.path.isfile(f"../test-data/{file_name}"):
        file = f"../test-data/{file_name}"
    elif os.path.isfile(f"./test-data/{file_name}"):
        file = f"./test-data/{file_name}"
    else:
        raise FileNotFoundError(f"Couldn't find test file `{file_name}`")

    data: pd.DataFrame = read_parquet_sensor_data(file)
    data["typeGroup"] = data["type"].map(sensor_data_type_group_map.get)
    data = (
        data.reset_index(drop=True)
        .pivot(index=["timestamp", "typeGroup"], columns=["type"], values="value")
        .droplevel("typeGroup")
    )
    data.index = pd.to_datetime(data.index, unit="ns", utc=True)
    return data
