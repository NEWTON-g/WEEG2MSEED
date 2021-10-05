import datetime
import numpy as np
import obspy
import pandas as pd

class WEEG2MSEED():

  """
  Class to convert Wee-g gravimeter data to mSEED using ObsPy
  Author: Mathijs Koymans, KNMI
  Last Updated: Oct. 2021
  """

  # Sample rate is 1.0
  SAMPLING_INT = 1.0
  QUALITY = "D"


  def __init__(self, network, station, location):

    """
    def WEEG2MSEED.__init__
    Initializes the converter: requires a SEED network, station, and location code
    """

    self.network = network
    self.station = station
    self.location = location
  

  def get_header(self, starttime, channel):

    """
    def WEEG2MSEED.get_header
    Returns a new dictionary representing the SEED header that is used by ObsPy
    """

    # Define the mSEED header
    # Sampling rate should be rounded to 6 decimals.. floating point issues
    return dict({
      "starttime": starttime,
      "network": self.network,
      "station": self.station,
      "location": self.location,
      "channel": channel,
      "mseed": {"dataquality": self.QUALITY},
      "sampling_rate": (1. / self.SAMPLING_INT)
    })


  def map_name(self, name):
  
    """
    def map_name
    Maps an input name to a tuple (dataframe entry, and mSEED channel code, gain)
    All values are converted to integers (COUNTS) for STEIM2 compression following the gain
    
    mSEED channel codes have three identifiers: 
      1. Sampling rate (M) for medium
      2. Instrument identifier (G) gravimeter, (D) barometer, (M) thermometer, (A) tilt
      3. Component (Z) vertical, (N) north, (E) east, (1 .. N) arbitrary numbering
    Refer to the mSEED manual
    """
  
    # Gravity codes
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


  def add_trace(self, stream, timestamps, data, start, end, channel):

    """
    def WEEG2MSEED.add_trace
    Adds a trace to the passed stream based on the start and end incides
    """

    samples = data[start:end].astype("int32")

    header = self.get_header(obspy.UTCDateTime(timestamps.iloc[start]), channel)
    trace = obspy.Trace(samples, header=header)

    print("Adding trace [%s]." % trace)

    # Report the timing mismatch due to irregular sampling

    if end is None:
      mismatch = obspy.UTCDateTime(timestamps.iloc[-1]) - trace.stats.endtime
    else:
      mismatch = obspy.UTCDateTime(timestamps.iloc[end - 1]) - trace.stats.endtime

    print("The current trace endtime mismatch is %.3fs." % np.abs(mismatch))

    stream.append(trace)


  def to_files(self, files, channel, stream):

      """
      def WEEG2MSEED.to_files
      Converts streams to mSEED files
      """

      # Here we will sort the streams
      # Seismological data is conventionally stored in daily files
      # Therefore, we will loop over all days between the start and the end date
      start_date = obspy.UTCDateTime(stream[0].stats.starttime.date)
      end_date = obspy.UTCDateTime(stream[-1].stats.starttime.date)

      print("Added a total of %d traces." % len(stream))
      print("Adding traces to the respective day files.")

      # One problem here is that if one day if spread in two files it overwrites the first file
      while(start_date <= end_date):

        # Filename is network, station, location, channel, quality (D), year, day of year delimited by a period
        filename = ".".join([
          self.network,
          self.station,
          self.location,
          channel,
          self.QUALITY,
          start_date.strftime("%Y"),
          start_date.strftime("%j")
        ])

        # Get the data beloning to a single day and write to the correct file
        st_day = stream.slice(start_date, start_date + datetime.timedelta(days=1))
        files.append((filename, channel + "." + self.QUALITY, st_day))

        # Increment the day
        start_date += datetime.timedelta(days=1)


  def get_continuous_traces(self, timestamps):

    """
    def WEEG2MSEED.get_continuous_traces
    Returns the indices of all end points of the continuous traces
    """

    # Get the true sampling interval between the samples to identify gaps in seconds (this is datetime64[ns])
    differences = 1E-9 * np.diff(timestamps).astype(np.float64)

    # Check whether the sampling interval is within a tolerance: otherwise we create a reference
    # to the index where the gap is. We will use these indices to create individual traces.
    indices = np.flatnonzero(
      (differences < self.SAMPLING_INT) |
      (differences > self.SAMPLING_INT)
    )

    # Add one to split on the correct sample since np.diff reduced the index by one
    indices += 1

    # Add final index because the final trace ends there..
    return np.append(indices, len(timestamps))


  def add_stream(self, files, df, name):

    """
    def WEEG2MSEED.add_stream
    Adds a stream
    """

    # Create an empty ObsPy stream to collect all traces
    stream = obspy.Stream()
   
    # Map the requested data file
    (channel, gain) = self.map_name(name)
   
    print("Converting channel %s to %s." % (name, channel))
   
    # Filter out NaN
    ndf = df[~np.isnan(df[name])]
    timestamps = ndf["TIME"]
   
    # Reference the data and convert to int32 for storage. mSEED cannot store long long (64-bit) integers.
    # Can we think of a clever trick? STEIM2 compression (factor 3) is available for integers, not for ints.
    data = (gain * np.array(ndf[name])).astype("int32")
   
    indices = self.get_continuous_traces(timestamps)

    # Here we start collecting the pandas data frame in to continuous traces without gaps
    # The index of the first trace is naturally 0
    start = 0
   
    # Go over the collected indices where there is a gap!
    for end in list(indices):
   
      print("Found gap in data outside of tolerance of length.")

      self.add_trace(stream, timestamps, data, start, end, channel)
   
      # Set the start to the end of the previous trace and proceed with the next trace
      start = end
   
    # Add to the file collection
    self.to_files(files, channel, stream)


  def convert(self, filename, names):

    """
    def WEEG2MSEED.convert
    Converts a file and the requested channels to mSEED files: returns an array of ObsPy streams ready for writing
    """

    print("Reading MEMS input file %s." % filename)

    # Date parsing function
    custom_date_parser = lambda x: datetime.datetime.strptime(x, "%Y%m%d_%H:%M:%S")

    # Collection of files to return after conversion
    files = list()

    # Read the supplied AQG datafile to a dataframe.
    # We use the timestamp (0) and the requested column index (see map_name)
    try:
      df = pd.read_csv(filename, delimiter=",", parse_dates=["TIME"], date_parser=custom_date_parser, usecols=range(0, 13))
    except pd.errors.ParserError:
      return files

    # Go over all the requested channels
    for name in names:
      self.add_stream(files, df, name)

    return files
