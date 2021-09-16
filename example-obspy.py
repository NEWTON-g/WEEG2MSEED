from obspy import read, read_inventory

def show(inventory, stream):

  # Have to remove the sensitivity to go to proper units
  #stream.remove_sensitivity(inventory)

  stream.plot()

if __name__ == "__main__":

  # Metadata
  inventory = read_inventory("2Q.NTG04.xml")

  # Read gravity channel
  grav = read("mseed/LGZ.D/2Q.NTG04..LGZ.D.2021.249")
  show(inventory, grav)

  # Read tilt X channel
  grav = read("mseed/LA1.D/2Q.NTG04..LA1.D.2021.249")
  show(inventory, grav)

  # Read tilt Z channel
  grav = read("mseed/LA2.D/2Q.NTG04..LA2.D.2021.249")
  show(inventory, grav)

  # Read temperature channel AD7195_1_CH1
  grav = read("mseed/LK1.D/2Q.NTG04..LK1.D.2021.249")
  show(inventory, grav)

  # Read temperature channel AD7195_1_CH2
  grav = read("mseed/LK2.D/2Q.NTG04..LK2.D.2021.249")
  show(inventory, grav)

  # Read temperature channel AD7195_2_CH1
  grav = read("mseed/LK3.D/2Q.NTG04..LK3.D.2021.249")
  show(inventory, grav)

  # Read temperature channel AD7195_2_CH2
  grav = read("mseed/LK4.D/2Q.NTG04..LK4.D.2021.249")
  show(inventory, grav)

  # Read temperature channel AD7195_3_CH1
  grav = read("mseed/LK5.D/2Q.NTG04..LK5.D.2021.249")
  show(inventory, grav)
