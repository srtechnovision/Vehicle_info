"""Pure-Python replacement for the FastAPI-based VIN decoder.

This file removes external dependencies (FastAPI, Pydantic) and provides:
- A simple CLI to decode a VIN
- A small stdlib HTTP server with a POST /decode/ endpoint that accepts JSON {"vin": "..."}

Run as CLI:
    python BIKE_IDENTIFY/main.py decode MAT62922XXXXXXXX

Run as server:
    python BIKE_IDENTIFY/main.py --serve --port 8000

The API mirrors the previous behavior and returns JSON:
{
  "Year": 2023,
  "Specs": { ... }
}

Errors are returned with appropriate HTTP status codes and JSON payloads.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import argparse
import json
from typing import Dict, Any

# Database and year map (kept from the original file)
YEAR_MAP = {
    'L': 2020,
    'M': 2021,
    'N': 2022,
    'P': 2023,
    'R': 2024,
    'S': 2025,
    'T': 2026,
}

EV_DATABASE = {
    "MAT62922": {
        "Make": "Tata",
        "Model": "Tigor EV",
        "Trim": "Standard",
        "Usable_Battery": "26 kWh",
        "Range": "315 km",
        "Warranty_Years": 8,
        "Warranty_KM": 160000,
    }
}


class VINDecodeError(Exception):
    """Custom exception for VIN decoding errors."""


def decode_vin(vin: str) -> Dict[str, Any]:
    """Decode the VIN using the simple in-memory database.

    Args:
        vin: VIN string (case-insensitive). Must be 17 characters.

    Returns:
        A dict containing Year and Specs.

    Raises:
        VINDecodeError: For validation errors (bad length, not found, etc.).
    """
    if not isinstance(vin, str):
        raise VINDecodeError("VIN must be a string.")

    vin = vin.upper().strip()

    if len(vin) != 17:
        raise VINDecodeError("VIN must be exactly 17 characters.")

    wmi = vin[0:3]
    vds = vin[3:8]
    # 10th character (index 9) represents model year in many VIN schemes
    year_char = vin[9]

    lookup_key = wmi + vds
    vehicle_data = EV_DATABASE.get(lookup_key)
    if vehicle_data is None:
        raise VINDecodeError("Vehicle specs not found in database.")

    return {"Year": YEAR_MAP.get(year_char, "Unknown"), "Specs": vehicle_data}


class DecodeHandler(BaseHTTPRequestHandler):
    def _set_json_response(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

    def do_POST(self):
        if self.path not in ("/decode/", "/decode"):
            self._set_json_response(404)
            self.wfile.write(json.dumps({"detail": "Not Found"}).encode())
            return

        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._set_json_response(400)
            self.wfile.write(json.dumps({"detail": "Empty request body"}).encode())
            return

        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
        except Exception:
            self._set_json_response(400)
            self.wfile.write(json.dumps({"detail": "Request body must be valid JSON"}).encode())
            return

        vin = data.get('vin') if isinstance(data, dict) else None
        try:
            result = decode_vin(vin)
            self._set_json_response(200)
            self.wfile.write(json.dumps(result).encode())
        except VINDecodeError as e:
            # Mirror FastAPI behavior: 400 for validation issues, 404 for not found
            msg = str(e)
            status = 400 if 'exactly 17' in msg or 'string' in msg or 'Empty' in msg else 404
            self._set_json_response(status)
            self.wfile.write(json.dumps({"detail": msg}).encode())

    def log_message(self, format: str, *args) -> None:  # reduce console noise
        return


def run_server(port: int) -> None:
    server = HTTPServer(('0.0.0.0', port), DecodeHandler)
    print(f"Serving decode endpoint on http://0.0.0.0:{port}/decode/ (POST JSON {'{\"vin\": \"...\"}'})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server")
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description='Pure-Python VIN decoder (no external deps)')
    subparsers = parser.add_subparsers(dest='command')

    # serve command
    parser.add_argument('--serve', action='store_true', help='Run a small HTTP server exposing POST /decode/')
    parser.add_argument('--port', type=int, default=8000, help='Port to serve on when --serve is used')

    # decode CLI (optional positional VIN)
    parser.add_argument('vin', nargs='?', help='VIN to decode (17 characters)')

    args = parser.parse_args()

    if args.serve:
        run_server(args.port)
        return

    if args.vin:
        try:
            res = decode_vin(args.vin)
            print(json.dumps(res, indent=2))
        except VINDecodeError as e:
            print(f"Error: {e}")
    else:
        # Interactive prompt
        vin = input('Enter VIN (17 chars): ').strip()
        try:
            res = decode_vin(vin)
            print(json.dumps(res, indent=2))
        except VINDecodeError as e:
            print(f"Error: {e}")


if __name__ == '__main__':
    main()
