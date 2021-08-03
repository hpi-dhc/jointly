from typing import List

import pandas as pd


def read_parquet_sensor_data(
    file: str = "assets/data.parquet",
) -> pd.DataFrame:
    df = pd.read_parquet(file)

    timestamp = df["timestamp"].explode(ignore_index=True)
    type = df["type"].explode(ignore_index=True)
    value = df["value"].explode(ignore_index=True)

    df = pd.concat([timestamp, type, value], axis="columns")
    return df


def pivot_parquet_sensor_data(data: pd.DataFrame):
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
    data["typeGroup"] = data["type"].map(sensor_data_type_group_map.get)
    data = (
        data.reset_index(drop=True)
        .pivot(index=["timestamp", "typeGroup"], columns=["type"], values="value")
        .droplevel("typeGroup")
    )
    data.index = pd.to_datetime(data.index, unit="ns", utc=True)
    return data
