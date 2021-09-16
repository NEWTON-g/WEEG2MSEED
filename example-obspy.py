from obspy import read, read_inventory

def show(inventory, stream):

  # Have to remove the sensitivity to go to proper units
  stream.remove_sensitivity(inventory)

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

  # Read temperature channel
  grav = read("mseed/LK1.D/2Q.NTG04..LK1.D.2021.249")
  show(inventory, grav)
