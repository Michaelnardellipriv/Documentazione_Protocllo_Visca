# ViscaOverIpSimulator

ViscaOverIpSimulator is a lightweight tool designed to quickly simulate VISCA over IP cameras. It allows developers to test and debug PTZ (Pan-Tilt-Zoom) camera commands without requiring physical hardware. The simulator supports TCP and UDP communication, handles common VISCA commands, and provides customizable responses for various camera operations.

## Features

- Simulates a VISCA over IP camera.
- Supports TCP and UDP communication.
- Handles common VISCA commands:
  - Power On/Off
  - Pan-Tilt-Zoom (PTZ) movement
  - Focus control (manual/auto)
  - Inquiry commands (e.g., pan/tilt position, zoom level, focus mode).
- Logs received commands and responses for easy debugging.
- Customizable responses and behavior.

## Usage

1. Start the simulator. By default, it listens on port 52381 for both TCP and UDP connections.
2. Send VISCA commands to the simulator using tools like Packet Sender or a custom application.
3. The simulator logs all received commands and sends appropriate responses.

## Contributing

Contributions are welcome! If you want to add new features, fix bugs, or improve documentation:
1. Fork the repository.
2. Create a new branch: git checkout -b feature-name.
3. Commit your changes: git commit -m 'Add some feature'.
4. Push to the branch: git push origin feature-name.
5. Open a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.