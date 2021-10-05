import os

from src.weeg2mseed import WEEG2MSEED

if __name__ == "__main__":

  """
  Script to convert AQG gravimeter data to mSEED using ObsPy
  Author: Mathijs Koymans, 2020
  """

  # Columns to write to mSEED: each will be a channel
  columns = [
    "CH4R",
    "AD7195_1_Ch1", "AD7195_1_Ch2", "AD7195_2_Ch1", "AD7195_2_Ch2", "AD7195_3_Ch1",
    "tilt_X", "tilt_Z"
  ]

  # Network identifier (NEWTON-g), station identifier (NTG04), and location ("")
  # https://www.fdsn.org/networks/detail/2Q_2020/
  convertor = WEEG2MSEED("2Q", "NTG04", "")

  # Paths to (read, write) (from, to):
  path = "data"
  path2 = "mseed"

  for file in os.listdir(path):

    if file.startswith("."):
      continue

    filepath = os.path.join(path, file)

    # Convert the input file to mSEED streams
    # Pass correct to add all gravity corrections
    files = convertor.convert(
      filepath,
      columns
    )

    # Write the streams to files
    for (filename, channel, stream) in files:

      print("Writing mSEED output file to %s." % filename)

      # Write to appropriate channel
      if not os.path.exists(os.path.join(path2, channel)):
        os.makedirs(os.path.join(path2, channel)) 

      stream.write(os.path.join(path2, channel, filename), format="MSEED")
