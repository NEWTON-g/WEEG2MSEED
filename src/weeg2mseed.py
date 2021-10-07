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
  
    # Channel code and gain to make floating point integers fit into 32 bit
    defs = {
      "CH4R": ("LGZ", 1E0),
      "AD7195_1_Ch1": ("LK1", 1E6),
      "AD7195_1_Ch2": ("LK2", 1E6),
      "AD7195_2_Ch1": ("LK3", 1E6),
      "AD7195_2_Ch2": ("LK4", 1E6),
      "AD7195_3_Ch1": ("LK5", 1E6),
      "tilt_X": ("LA1", 1E6),
      "tilt_Z": ("LA2", 1E6)
    }

    # Unknown
    if name not in defs:
      raise ValueError("Invalid field %s requested." % name)

    return defs[name]


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
    channel, gain = self.map_name(name)
   
    print("Converting channel %s to %s." % (name, channel))
   
    # Filter out any NaN in the particular column
    ndf = df[~np.isnan(df[name])]

    # Reference the timestamp column 
    timestamps = ndf["TIME"]
   
    # Use the gain to make floating point measurements to digital counts (as 32-bit): this is corrected for in the metadata
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


  def parse_date(self, x):

    """
    def WEEG2MSEED.parse_date
    Definition to parse the timestamp used in the Wee-g format
    """

    return datetime.datetime.strptime(x, "%Y%m%d_%H:%M:%S")


  def convert(self, filename, names):

    """
    def WEEG2MSEED.convert
    Converts a file and the requested channels to mSEED files: returns an array of ObsPy streams ready for writing
    """

    print("Reading MEMS input file %s." % filename)

    # Collection of files to return after conversion
    files = list()

    # Read the supplied Wee-g datafile to a dataframe.
    try:
      df = pd.read_csv(filename, parse_dates=["TIME"], date_parser=self.parse_date, usecols=range(0, 13))
    except Exception:
      return files

    # Go over all the requested channels
    for name in names:
      self.add_stream(files, df, name)

    return files
