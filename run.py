import os

from src.mems2mseed import convert

if __name__ == "__main__":

  """
  Script to convert AQG gravimeter data to mSEED using ObsPy
  Author: Mathijs Koymans, 2020
  """

  # Columns to write to mSEED: each will be a channel
  columns = [
    "raw_gravity",
  ]

  # Network identifier (NEWTON-g), station identifier (AQG), and location ("")
  network = "2Q"
  station = "NTG04"
  location = ""

  # Paths to (read, write) (from, to):
  path = "data"
  path2 = "mseed"

  for file in os.listdir(path):

    filepath = os.path.join(path, file)

    # Convert the input file to mSEED streams
    # Pass correct to add all gravity corrections
    files = convert(
      filepath,
      network,
      station,
      location,
      columns
    )

    # Write the streams to files
    for (filename, channel, stream) in files:

      print("Writing mSEED output file to %s." % filename)

      # Write to appropriate channel
      if not os.path.exists(os.path.join(path2, channel)):
        os.makedirs(os.path.join(path2, channel)) 

      stream.write(os.path.join(path2, channel, filename), format="MSEED")
