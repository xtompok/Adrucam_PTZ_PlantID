# Arducam PTZ for PlantID
Automated search and periodic capture of plants for Plant.ID with Arducam PTZ camera

## Filename specification
Filename contains following information in this order:
	* Prefix (`p`) - prefix common for given installation
	* Timestamp (`t`) - UNIX timetamp, rounded to seconds
	* Pan (`P`) - pan angle in degrees
	* Tilt (`T`) - tilt angle in degrees
	* Zoom (`Z`) - zoom level (0--100)
	* Focus (`F`) - focus level (0--10000)

Example filename: `pobyvak_t1645267120_P10_T20_Z60_F5000.jpg`
