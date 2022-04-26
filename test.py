from obspy import read, read_inventory
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import os

def parse_date(x):

  """
  def WEEG2MSEED.parse_date
  Definition to parse the timestamp used in the Wee-g format
  """

  return datetime.datetime.strptime(x, "%Y%m%d_%H:%M:%S")

if __name__ == "__main__":

  """
  Function to test conversion of AQG data to mSEED
  """

  filepath = os.path.join("data", "NTG04.20220425.grv")
  df = pd.read_csv(filepath, parse_dates=["TIME"], float_precision='round_trip', date_parser=parse_date)
  inv = read_inventory("2Q.NTG04.xml")

  tuples = [
    ("LGZ.D", "CH4R"),
    ("LK1.D", "AD7195_1_Ch1"),
    ("LK2.D", "AD7195_1_Ch2"),
    ("LK3.D", "AD7195_2_Ch1"),
    ("LK4.D", "AD7195_2_Ch2"),
    ("LK5.D", "AD7195_3_Ch1"),
    ("LA1.D", "tilt_X"),
    ("LA2.D", "tilt_Z")
  ]
  
  for (channel, column) in tuples:
  
    try:
      stream = read(os.path.join("mseed", channel, "2Q.NTG04..%s.2022.115" % channel))
    except:
      continue
  
    stream.remove_sensitivity(inv)
    
    for trace in stream:
      plt.plot(trace.times("matplotlib"), trace.data, color="grey")
    
    plt.title(channel)

    # microGal to M/S**2: multiply by 1E-8
    if channel == "LGZ.D": 
      gain = 1E-8
    else:
      gain = 1

    plt.plot(df["TIME"], gain * df[column])

    plt.show()
