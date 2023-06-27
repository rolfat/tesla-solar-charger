# tesla-solar-charger

Python script to match Tesla charging with solar electricity production

This is useful when net metering is not available, or when the cost of electricty sent back to the grid is less than the cost of electricity consumed from the grid. The idea is that when extra solar power is available, the tesla battery is charged.

The first time it runs, the teslapy module will prompt for API key capture.

Edit the environment variables to put in your tesla account email address, home latitude and longitude (make sure to use negative longitude for western hemisphere). Run main.py. It will fetch current status, set the Tesla charging appropriately, and then sleep for 15 minutes to repeat.

# Edge cases
-  Overestimates surplus power if charger just recently turned on. Assumes charger has been drawing for the full lookback window.
- Stops charging after operating hours

# Feature requests
- use scheduler instead of `sleep()`
- support multiple vehicles, solar devices, and users
- frontend to configure settings (lat/long, op hours, max amps, auto-shutoff, etc)
- model to predict next interval production/consumption using historical data

# Build notes
- dependencies installed with pip (use "Shell" in replit)
  
# License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>. 

