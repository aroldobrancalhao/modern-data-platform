from pyspark.sql import DataFrame

from common.constants import FileFormat
from common.constants import SaveMode


def write_dataset(
    dataframe: DataFrame,
    path: str,
    file_format: FileFormat = FileFormat.DELTA,
    mode: SaveMode = SaveMode.OVERWRITE,
) -> None:

    (
        dataframe.write
        .format(file_format.value)
        .mode(mode.value)
        .save(path)
    )