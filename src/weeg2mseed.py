import pandas as pd
import matplotlib.pyplot as plt
import sys
import datetime
import numpy as np
import obspy

def map_name(name):

  """
  def map_name
  Maps an input name to a tuple (dataframe entry, and mSEED channel code, gain)
  All values are converted to integers for STEIM2 compression
  
  mSEED channel codes have three identifiers: 
    1. Sampling rate (M) for medium
    2. Instrument identifier (G) gravimeter, (D) barometer, (M) thermometer, (A) tilt
    3. Component (Z) vertical, (N) north, (E) east, (1 .. N) arbitrary numbering
  Refer to the mSEED manual
  """

  # Gravity codes: quality code will be different
  if name == "CH4R":
    return ("LGZ", 1E0)

  # Temperature channels
  elif name == "AD7195_1_Ch1":
    return ("LK1", 1E6)
  elif name == "AD7195_1_Ch2":
    return ("LK2", 1E6)
  elif name == "AD7195_2_Ch1":
    return ("LK3", 1E6)
  elif name == "AD7195_2_Ch2":
    return ("LK4", 1E6)
  elif name == "AD7195_3_Ch1":
    return ("LK5", 1E6)

  # Tilts
  elif name == "tilt_X":
    return ("LA1", 1E6)
  elif name == "tilt_Z":
    return ("LA2", 1E6)

  else:
    raise ValueError("Invalid field %s requested." % name)

def convert(filename, network, station, location, names):

  """
  Script to convert AQG gravimeter data to mSEED using ObsPy
  Author: Mathijs Koymans, 2020
  """

  # Sampling interval tolerance (s)
  EPSILON = 0.01
  # The AQG samples at 0.54 seconds instead of 2Hz
  SAMPLING_INT = 1

  quality = "D"

  print("Reading MEMS input file %s." % filename)

  # Date parsing function
  custom_date_parser = lambda x: datetime.datetime.strptime(x, "%Y%m%d_%H:%M:%S")

  # Read the supplied AQG datafile to a dataframe.
  # We use the timestamp (0) and the requested column index (see map_name)
  df = pd.read_csv(filename, delimiter=",", parse_dates=["TIME"], date_parser=custom_date_parser, usecols=range(0, 13))

  # Get the true sampling interval between the samples to identify gaps
  differences = 1E-9 * np.diff(df["TIME"]).astype(np.float64)

  # Check whether the sampling interval is within a tolerance: otherwise we create a reference
  # to the index where the gap is. We will use these indices to create individual traces.
  indices = np.flatnonzero(
    (differences < (SAMPLING_INT - EPSILON)) |
    (differences > (SAMPLING_INT + EPSILON))
  )

  # Add one to split on the correct sample since np.diff reduced the index by one
  indices += 1
  
  # Collection of files to return after conversion
  files = list()

  # Go over all the requested channels
  for name in names:

    # Create an empty ObsPy stream to collect all traces
    st = obspy.Stream()

    # Map the requested data file
    (channel, gain) = map_name(name)

    # Define the mSEED header
    # Sampling rate should be rounded to 6 decimals.. floating point issues
    header = dict({
      "starttime": None,
      "network": network,
      "station": station,
      "location": location,
      "channel": channel,
      "mseed": {"dataquality": quality},
      "sampling_rate": np.round((1. / SAMPLING_INT), 6)
    })

    ndf = df[~np.isnan(df[name])]

    # Reference the data and convert to int32 for storage. mSEED cannot store long long (64-bit) integers.
    # Can we think of a clever trick? STEIM2 compression (factor 3) is available for integers, not for ints.
    data = (int(gain) * np.array(ndf[name])).astype("int32")
    timestamps = ndf["TIME"]

    # Calculate the bitwise xor of all gravity data samples as checksum
    # After writing to mSEED, we apply xor again and the result should come down to 0 
    checksum = np.bitwise_xor.reduce(data)

    # Here we start collecting the pandas data frame in to continuous traces without gaps
    # The index of the first trace is naturally 0
    start = 0

    # Go over the collected indices where there is a gap!
    for end in list(indices):

      # Alert client of the gap size
      print("Found gap in data outside of tolerance of length: %.3fs. Starting new trace." % differences[end - 1])

      # Set the start time of the trace equal to the first sample of the trace
      header["starttime"] = obspy.UTCDateTime(timestamps.iloc[start])

      # Get the array slice between start & end and add it to the existing stream
      tr = obspy.Trace(data[start:end], header=header)

      print("Adding trace [%s]." % tr)

      # Report the timing mismatch due to irregular sampling
      mismatch = obspy.UTCDateTime(timestamps.iloc[end - 1]) - tr.stats.endtime
      print("The trace endtime mismatch is %.3fs." % np.abs(mismatch))

      # XOR with the existing checksum: eventually this should reduce back to 0
      checksum ^= np.bitwise_xor.reduce(tr.data.astype("int32"))

      # Save the trace to the stream
      st.append(tr)

      # Set the start to the end of the previous trace and proceed with the next trace
      start = end

    # Remember to append the remaining trace after the last gap
    # This does not happen automatically but is the same procedure as inside the while loop
    header["starttime"] = obspy.UTCDateTime(timestamps.iloc[start])
    tr = obspy.Trace(data[start:].astype("int32"), header=header)
    mismatch = obspy.UTCDateTime(timestamps.iloc[len(timestamps) - 1]) - tr.stats.endtime
    print("Adding remaining trace [%s]." % tr)
    print("The current trace endtime mismatch is %.3fs." % np.abs(mismatch))
    st.append(tr)

    # Add the checksum of the final trace
    checksum ^= np.bitwise_xor.reduce(tr.data.astype("int32"))
    
    # Confirm that the checksum is zero and therefore correct
    if checksum != 0:
      raise AssertionError("Data xor checksum is incorrect! Not all samples were written correctly.")

    # Here we will sort the streams
    # Seismological data is conventionally stored in daily files
    # Therefore, we will loop over all days between the start and the end date
    start_date = obspy.UTCDateTime(st[0].stats.starttime.date)
    end_date = obspy.UTCDateTime(st[-1].stats.starttime.date)

    print("Added a total of %d traces." % len(st))
    print("Adding traces to the respective day files.")

    # One problem here is that if one day if spread in two files it overwrites the first file
    while(start_date <= end_date):

      # Filename is network, station, location, channel, quality (D), year, day of year delimited by a period
      filename = ".".join([
        network,
        station,
        location,
        channel,
        quality,
        start_date.strftime("%Y"),
        start_date.strftime("%j")
      ])

      # Get the data beloning to a single day and write to the correct file
      st_day = st.slice(start_date, start_date + datetime.timedelta(days=1))
      files.append((filename, channel + "." + quality, st_day))

      # Increment the day
      start_date += datetime.timedelta(days=1)

  # Ready for saving to disk!
  return files
